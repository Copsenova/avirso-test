import numpy as np
import relief_images as ri


def portrait(h=128, w=100):
    rgb = np.zeros((h, w, 3), np.uint8); rgb[..., 0] = np.arange(w)[None, :] * 2; rgb[..., 1] = 120
    m = np.zeros((h, w), np.uint8); m[20:120, 25:75] = 255
    d = np.zeros((h, w), np.uint8); d[20:120, 25:75] = 200; d[50:70, 45:55] = 255      # « nez » plus proche
    return rgb, m, d


def test_vues_carrees_et_angles_symetriques():
    v = ri.vues(*portrait(), angles=[-12, 0, 12], cote=96)
    assert [a for a, _ in v] == [-12, 0, 12]
    assert all(im.shape == (96, 96, 4) for _, im in v)


def test_vue_de_face_identique_au_portrait_detoure():
    rgb, m, d = portrait()
    (a, im), = ri.vues(rgb, m, d, angles=[0], cote=128)
    assert a == 0
    x0 = (128 - 100) // 2
    assert np.abs(im[:, x0:x0 + 100, 3].astype(int) - m.astype(int)).max() <= 1
    assert np.abs(im[60, x0 + 50, :3].astype(int) - rgb[60, 50].astype(int)).max() <= 2


def test_la_rotation_avance_le_nez_et_recule_le_contour():
    rgb, m, d = portrait()
    (_, c), (_, dr) = ri.vues(rgb, m, d, angles=[0, 12], cote=128)
    def bord_gauche(im):
        return int(np.nonzero(im[100, :, 3] > 127)[0][0])
    def nez(im):      # colonne du pixel le plus clair du « nez » (rouge = abscisse dans le portrait)
        return float(np.mean(np.nonzero((im[60, :, 3] > 127) & (np.abs(im[60, :, 0].astype(int) - 100) < 3))[0]))
    assert ri.decalage_nez(d, 12) > 0 and ri.decalage_nez(d, -12) == -ri.decalage_nez(d, 12)
    # sens opposés : le point le plus proche part d'un côté, le contour (plus loin que l'axe) de l'autre
    assert np.sign(nez(dr) - nez(c)) != np.sign(bord_gauche(dr) - bord_gauche(c)) or bord_gauche(dr) == bord_gauche(c)
    assert nez(dr) != nez(c)


def test_webp_avec_transparence():
    (_, im), = ri.vues(*portrait(), angles=[0], cote=64)
    b = ri.webp(im)
    assert b[:4] == b"RIFF" and b[8:12] == b"WEBP"


def test_pas_de_dedoublement_quand_une_partie_en_cache_une_autre():
    # une bande verticale très proche (« oreille » vue de face) devant un fond de visage plus loin : en tournant fort,
    # la bande doit masquer ce qui est derrière, et apparaître UNE seule fois sur chaque ligne
    h, w = 64, 80
    rgb = np.full((h, w, 3), 90, np.uint8); rgb[:, 30:34] = (250, 20, 20)
    m = np.zeros((h, w), np.uint8); m[:, 10:70] = 255
    d = np.full((h, w), 60, np.uint8); d[:, 30:34] = 255
    (_, im), = ri.vues(rgb, m, d, angles=[25], cote=64)
    rouge = (im[32, :, 0] > 200) & (im[32, :, 1] < 80) & (im[32, :, 3] > 127)
    runs = np.diff(np.concatenate([[0], rouge.astype(int), [0]]))
    assert (runs == 1).sum() == 1, f"bande rouge en {(runs == 1).sum()} morceaux"
