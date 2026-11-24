# AVIRSO, essai : une tête qui tourne à partir de quelques vraies photos (face, trois-quarts).
#
# Principe :
#   1. LivePortrait (code et poids sous licence MIT) fait tourner chaque vraie photo de quelques degrés.
#      Chaque angle affiché part de la vraie photo la plus proche : le modèle invente le moins possible.
#   2. Le grain fin (cheveux, barbe, peau) est repris de la vraie photo en haute définition, déplacé au
#      même endroit par flot optique (OpenCV), puis posé sur l'image générée. Rien n'est inventé à cette étape.
#   3. Entre deux vraies photos, on passe de l'une à l'autre par une courte transition recalée.
#   4. La tête est détourée (modèle « selfie multiclass » de MediaPipe, Apache 2.0) quand c'est possible.
#
# À lancer depuis le dossier de LivePortrait :
#   python tete.py sortie photo1 photo2 photo3
# Réglages par variables d'environnement : PAS (degrés entre deux images, 1.5), MARGE (degrés au-delà de la
# photo la plus tournée, 8), TAILLE (côté des images produites, 1024), FOND (1 pour détourer, 0 sinon).
# Les images produites sont générées par un modèle : ce ne sont pas des photos.
import os, sys, time, yaml, numpy as np, cv2, torch
from PIL import Image, ImageOps
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass
from src.utils.helper import load_model
from src.utils.camera import headpose_pred_to_degree, get_rotation_matrix

PAS = float(os.environ.get('PAS', 1.5))
MARGE = float(os.environ.get('MARGE', 8))
TAILLE = int(os.environ.get('TAILLE', 1024))
FOND = os.environ.get('FOND', '1') == '1'
RECOUVRE = 2.5          # demi-largeur, en degrés, de la transition entre deux vraies photos
HAUTEUR_TETE = 0.61    # part de la hauteur du cadre occupée par la tête (du haut des cheveux au menton)
CADRE = os.environ.get('CADRE')
CADRE = [float(v) for v in CADRE.split(',')] if CADRE else None

dev = 'cuda' if torch.cuda.is_available() else 'cpu'
print('calcul sur :', dev)
cfg = yaml.safe_load(open('src/config/models.yaml'))
F = load_model('pw/appearance_feature_extractor.pth', cfg, dev, 'appearance_feature_extractor')
M = load_model('pw/motion_extractor.pth', cfg, dev, 'motion_extractor')
W = load_model('pw/warping_module.pth', cfg, dev, 'warping_module')
G = load_model('pw/spade_generator.pth', cfg, dev, 'spade_generator')
S = load_model('pw/stitching_retargeting_module.pth', cfg, dev, 'stitching_retargeting_module')

sortie = sys.argv[1]
chemins = sys.argv[2:]
assert chemins, 'donnez au moins une photo'


def lire(chemin):
    im = ImageOps.exif_transpose(Image.open(chemin)).convert('RGB')
    return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


def cadrer(img, cx, cy, cote, taille):
    """Carré de côté `cote` centré en (cx, cy), bords prolongés, ramené à `taille` pixels."""
    cote = int(round(cote))
    b = cv2.copyMakeBorder(img, cote, cote, cote, cote, cv2.BORDER_REPLICATE)
    x0, y0 = int(round(cx - cote / 2)) + cote, int(round(cy - cote / 2)) + cote
    x0 = min(max(x0, 0), b.shape[1] - cote); y0 = min(max(y0, 0), b.shape[0] - cote)
    c = b[y0:y0 + cote, x0:x0 + cote]
    return cv2.resize(c, (taille, taille), interpolation=cv2.INTER_AREA if cote > taille else cv2.INTER_CUBIC)


def tenseur(bgr256):
    rgb = cv2.cvtColor(bgr256, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    return torch.from_numpy(rgb).permute(2, 0, 1)[None].to(dev)


def mesurer(x):
    """Pose, points et taille de la tête vus par le modèle."""
    k = M(x)
    p, y, r = [headpose_pred_to_degree(k[n])[:, None] for n in ('pitch', 'yaw', 'roll')]
    t = k['t'].clone(); t[:, 2] = 0
    return dict(pitch=p, yaw=y, roll=r, kp=k['kp'].reshape(1, -1, 3), exp=k['exp'].reshape(1, -1, 3), scale=k['scale'], t=t)


def poser(k, pitch, yaw, roll, scale, t):
    R = get_rotation_matrix(pitch, yaw, roll)
    p = (k['kp'] @ R + k['exp']) * scale[..., None]
    p[:, :, 0:2] += t[:, None, 0:2]
    return p


def deg(v):
    return torch.tensor([[float(v)]], device=dev)


# ---------- 0. découpe de la personne (sert au cadrage et au détourage) ----------
classes = None
try:
    import tensorflow as tf
    tf.config.set_visible_devices([], 'GPU')
    _it = tf.lite.Interpreter(model_path='pw/selfie_multiclass_256x256.tflite')
    _it.allocate_tensors()
    _e, _s = _it.get_input_details()[0], _it.get_output_details()[0]

    def classes(bgr):
        """Probabilités par pixel, en 256 px : fond, cheveux, peau du corps, peau du visage, vêtements, autres."""
        x = cv2.cvtColor(cv2.resize(bgr, (256, 256), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        _it.set_tensor(_e['index'], x[None]); _it.invoke()
        o = _it.get_tensor(_s['index'])[0]
        if o.min() < 0 or o.max() > 1:
            o = np.exp(o - o.max(-1, keepdims=True)); o /= o.sum(-1, keepdims=True)
        return o
    print('découpe de la personne : active')
except Exception as e:
    classes = None
    print('découpe de la personne : indisponible (', type(e).__name__, str(e)[:120], ') : cadrage central, fond gardé')


def boite_tete(bgr):
    """Boîte de la tête (cheveux et peau du visage) en fractions du cadre : x0, y0, x1, y1. None si introuvable."""
    c = classes(bgr).argmax(-1)
    m = ((c == 1) | (c == 3)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n < 2:
        return None
    g = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = st[g, :4]
    return x / 256, y / 256, (x + w) / 256, (y + h) / 256


def detourer(bgr):
    a = np.clip(((1 - classes(bgr)[..., 0]) - 0.35) / 0.4, 0, 1)
    return np.clip(cv2.resize(a, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_CUBIC), 0, 1)[..., None]


# ---------- 1. cadrage et mesure de chaque vraie photo ----------
photos = []
with torch.no_grad():
    for ch in chemins:
        img = lire(ch)
        H0, W0 = img.shape[:2]
        cote = 0.86 * H0 if W0 >= H0 else 0.98 * W0
        cx, cy = W0 / 2, (0.45 if W0 >= H0 else 0.42) * H0
        if CADRE:      # cadrage imposé, en fractions : centre x, centre y, côté (du petit côté)
            cx, cy, cote = CADRE[0] * W0, CADRE[1] * H0, CADRE[2] * min(W0, H0)
        if classes is not None and not CADRE:      # deux passes : on resserre le cadre sur la tête
            for tour in range(2):
                bt = boite_tete(cadrer(img, cx, cy, cote, 256))
                if bt is None:
                    print(os.path.basename(ch), ': tête non trouvée, cadrage central gardé')
                    break
                hx, hy = cx + ((bt[0] + bt[2]) / 2 - 0.5) * cote, cy + ((bt[1] + bt[3]) / 2 - 0.5) * cote
                cote = (bt[3] - bt[1]) * cote / HAUTEUR_TETE
                cx, cy = hx, hy - 0.01 * cote
        net = cadrer(img, cx, cy, cote, TAILLE)
        x = tenseur(cadrer(img, cx, cy, cote, 256))
        k = mesurer(x)
        ph = dict(nom=os.path.basename(ch), net=net, fs=F(x), k=k, yaw=float(k['yaw']), pitch=float(k['pitch']), roll=float(k['roll']))
        ph['ks'] = poser(k, k['pitch'], k['yaw'], k['roll'], k['scale'], k['t'])
        photos.append(ph)
        print(f"{ph['nom']} : lacet {ph['yaw']:+.1f}°, tangage {ph['pitch']:+.1f}°, roulis {ph['roll']:+.1f}° | "
              f"cadre de {cote:.0f} px centré en {cx / W0:.2f},{cy / H0:.2f} (photo de {W0}x{H0})")

photos.sort(key=lambda p: p['yaw'])
lacets = np.array([p['yaw'] for p in photos])
if len(photos) > 1 and np.min(np.diff(lacets)) < 4:
    print('attention : deux photos ont presque le même angle')
ech_c = torch.stack([p['k']['scale'] for p in photos]).mean(0)
t_c = torch.stack([p['k']['t'] for p in photos]).mean(0)
tang = lambda a: float(np.interp(a, lacets, [p['pitch'] for p in photos]))
roul = lambda a: float(np.interp(a, lacets, [p['roll'] for p in photos]))


def generer(ph, kd):
    n = kd.shape[1]
    d = S['stitching'](torch.cat([ph['ks'].reshape(1, -1), kd.reshape(1, -1)], 1))
    kd = kd + d[..., :3 * n].reshape(1, n, 3)
    kd[..., :2] += d[..., 3 * n:3 * n + 2].reshape(1, 1, 2)
    im = G(feature=W(ph['fs'], kp_source=ph['ks'], kp_driving=kd)['out'])
    a = (im[0].permute(1, 2, 0).clamp(0, 1).float().cpu().numpy() * 255).astype(np.uint8)
    a = cv2.cvtColor(a, cv2.COLOR_RGB2BGR)
    return a if a.shape[0] == TAILLE else cv2.resize(a, (TAILLE, TAILLE), interpolation=cv2.INTER_CUBIC)


# ---------- 2. grain de la vraie photo ----------
gris = lambda a: cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
try:
    _dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    flot = lambda a, b: _dis.calc(a, b, None)
except AttributeError:
    flot = lambda a, b: cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 5, 31, 5, 7, 1.5, 0)
_gx, _gy = np.meshgrid(np.arange(TAILLE, dtype=np.float32), np.arange(TAILLE, dtype=np.float32))


def tordre(img, f, part=1.0):
    return cv2.remap(img, _gx + part * f[..., 0], _gy + part * f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


SIG = 3.0 * TAILLE / 1024


def grain(ph, gt):
    """Pose sur l'image générée `gt` le détail fin de la vraie photo, déplacé au même endroit."""
    f = flot(gris(gt), gris(ph['g0']))
    r = tordre(ph['net_cale'], f).astype(np.float32)
    bas_r = cv2.GaussianBlur(r, (0, 0), SIG)
    bas_g = cv2.GaussianBlur(gt.astype(np.float32), (0, 0), SIG)
    # là où la vraie photo déplacée ne ressemble plus à l'image générée (zone cachée, flot raté), on n'ajoute rien
    accord = np.exp(-(np.abs(bas_r - bas_g).mean(2) / 18.0) ** 2)
    m = cv2.GaussianBlur(accord, (0, 0), SIG)[..., None]
    return np.clip(gt.astype(np.float32) + m * (r - bas_r), 0, 255).astype(np.uint8)


# ---------- 3. fond ----------
_y = np.linspace(0, 1, TAILLE, dtype=np.float32)[:, None, None]
ARRIERE = (np.array([[[26, 20, 18]]], np.float32) * (1 - _y) + np.array([[[12, 10, 9]]], np.float32) * _y) * np.ones((1, TAILLE, 1), np.float32)


def finir(bgr):
    if classes is None or not FOND:
        return bgr
    a = detourer(bgr)
    return (a * bgr.astype(np.float32) + (1 - a) * ARRIERE).astype(np.uint8)


# ---------- 4. toutes les images ----------
angles = np.arange(lacets[0] - MARGE, lacets[-1] + MARGE + 1e-6, PAS)
milieux = (lacets[:-1] + lacets[1:]) / 2
images, durees = [], []
with torch.no_grad():
    t0 = time.time()
    for ph in photos:      # image reconstruite à la pose de la photo, puis vraie photo calée dessus
        ph['g0'] = generer(ph, ph['ks'].clone())
        ph['net_cale'] = tordre(ph['net'], flot(gris(ph['g0']), gris(ph['net'])))
    print('préparation %.1f s' % (time.time() - t0))

    def vue(i, a):
        ph = photos[i]
        kd = poser(ph['k'], deg(tang(a)), deg(a), deg(roul(a)), ech_c, t_c)
        return grain(ph, generer(ph, kd))

    for a in angles:
        t0 = time.time()
        i = int(np.argmin(np.abs(lacets - a)))
        j = None
        if len(milieux):
            q = int(np.argmin(np.abs(milieux - a)))
            if abs(a - milieux[q]) < RECOUVRE:
                i, j = q, q + 1
        A = vue(i, a)
        if j is not None:      # transition : les deux images glissent l'une vers l'autre, puis se fondent
            B = vue(j, a)
            w = (a - (milieux[i] - RECOUVRE)) / (2 * RECOUVRE)
            w = float(w * w * (3 - 2 * w))
            fab, fba = flot(gris(A), gris(B)), flot(gris(B), gris(A))
            # A glisse d'une fraction w vers B, B d'une fraction 1-w vers A (déformation inverse approchée)
            A2 = tordre(A, fba, w)
            B2 = tordre(B, fab, 1 - w)
            A = cv2.addWeighted(A2, 1 - w, B2, w, 0)
        images.append(finir(A))
        durees.append(time.time() - t0)

print(f'{len(images)} images de {TAILLE} px, de {angles[0]:+.1f}° à {angles[-1]:+.1f}°, {np.mean(durees):.2f} s par image (max {np.max(durees):.2f}) sur {dev}')
os.makedirs(os.path.dirname(sortie) or '.', exist_ok=True)
for n, im in enumerate(images):
    cv2.imwrite(f'{sortie}_{n:03d}.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 92])
choix = [0, len(images) // 4, len(images) // 2, 3 * len(images) // 4, len(images) - 1]
cv2.imwrite(f'{sortie}_planche.jpg', np.concatenate([cv2.resize(images[n], (512, 512), interpolation=cv2.INTER_AREA) for n in choix], 1))
for ph in photos:
    cv2.imwrite(f"{sortie}_origine_{ph['yaw']:+04.0f}.jpg", ph['net'])
try:
    import imageio.v2 as imageio
    suite = images + images[::-1]
    imageio.mimsave(f'{sortie}.mp4', [im[:, :, ::-1] for im in suite], fps=30, macro_block_size=1)
    print('animation :', f'{sortie}.mp4')
except Exception as e:
    print('animation non écrite :', type(e).__name__, str(e)[:160])
