# Portrait studio en relief (27/11) : à partir du portrait retouché, de son détourage et de sa profondeur, fabrique la suite d'images
# que l'aperçu fait tourner au doigt (même format que l'ancienne « tête qui tourne » : images carrées, transparentes, angles en degrés).
# Le visage pivote légèrement autour d'un axe vertical ; le contour reste fixe, seul le relief intérieur (nez, joues) se déplace.
import io, math
import numpy as np

RELIEF = 0.32      # même amplitude que la visionneuse validée le 27/11 (rapportée à la hauteur de l image : 1,92)


def _profondeur_lissee(masque: np.ndarray, prof: np.ndarray) -> tuple[np.ndarray, float]:
    """Profondeur lissée, prolongée hors du détourage par la valeur du point de la silhouette le plus proche ; renvoie aussi la
    profondeur médiane de la silhouette : c'est l'axe de rotation (le nez avance d'un côté, le contour recule de l'autre)."""
    import cv2
    m = masque > 127
    d = cv2.GaussianBlur(prof.astype(np.float32), (0, 0), 2)
    if m.any() and not m.all():
        # étiquette de chaque pixel = point de la silhouette le plus proche (numérotés de 1 à N dans l'ordre de lecture)
        lab = cv2.distanceTransformWithLabels((~m).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)[1]
        ys, xs = np.nonzero(m)
        k = lab[~m] - 1
        d = d.copy(); d[~m] = d[ys[k], xs[k]]
    centre = float(np.median(d[m])) if m.any() else 128.0
    return d, centre


def _decalage_px(d: np.ndarray, bord: float, h: int) -> np.ndarray:
    return (d - bord) / 255.0 * RELIEF / 1.92 * h


def decalage_nez(prof: np.ndarray, angle: float) -> float:
    """Déplacement horizontal (px) du point le plus proche pour un angle donné (sert aux tests et au réglage)."""
    h = prof.shape[0]
    return round(math.sin(math.radians(angle)) * float(prof.max() - np.median(prof)) / 255.0 * RELIEF / 1.92 * h, 4)


def _carte_inverse(xp: np.ndarray, z: np.ndarray, w: int) -> np.ndarray:
    """Projection vers l'avant, ligne par ligne : chaque segment [x, x+1] du portrait est posé sur l'image tournée ; quand
    plusieurs segments tombent sur le même pixel, le plus proche de l'objectif l'emporte. Rend, pour chaque pixel de l'image
    tournée, l'abscisse à lire dans le portrait (−1 : rien, donc transparent)."""
    h = xp.shape[0]
    a, b = xp[:, :-1], xp[:, 1:]; za, zb = z[:, :-1], z[:, 1:]
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    base = np.ceil(lo - 1e-3).astype(np.int64); n = int(np.ceil((hi - lo).max())) + 1 if lo.size else 0
    rang = np.broadcast_to(np.arange(h)[:, None], a.shape); x0 = np.arange(w - 1, dtype=np.float32)[None, :]
    meilleur = np.full(h * w, -np.inf, np.float32); source = np.full(h * w, -1.0, np.float32)
    candidats = []
    for k in range(n):
        u = base + k
        ok = (u <= hi + 1e-3) & (u >= 0) & (u < w)
        d = np.where(np.abs(b - a) < 1e-6, 1.0, b - a)
        tt = np.clip((u - a) / d, 0, 1)
        zz = (za + (zb - za) * tt).astype(np.float32)
        idx = (rang * w + u)[ok]; candidats.append((idx, zz[ok], (x0 + tt)[ok]))
        np.maximum.at(meilleur, idx, zz[ok])
    for idx, zz, xs in candidats:
        g = zz >= meilleur[idx]
        source[idx[g]] = xs[g]
    return source.reshape(h, w)


def vues(rgb: np.ndarray, masque: np.ndarray, prof: np.ndarray, angles=range(-12, 13, 2), cote: int = 1024) -> list[tuple[float, np.ndarray]]:
    """Renvoie [(angle, image RGBA cote×cote)] : le portrait (mis à la hauteur `cote`, centré) tourné de chaque angle."""
    import cv2
    h, w = masque.shape
    d, bord = _profondeur_lissee(masque, prof)
    z = _decalage_px(d, bord, h)
    rgba = np.dstack([rgb, masque]).astype(np.uint8)
    cx = (w - 1) / 2
    ys, us = np.mgrid[0:h, 0:w].astype(np.float32)
    s = cote / h; lw = int(round(w * s)); x0 = (cote - lw) // 2
    sortie = []
    zb = np.where(masque > 127, z, -1e9).astype(np.float32)      # le fond ne cache jamais le visage
    X = np.arange(w, dtype=np.float32)[None, :]
    for a in angles:
        t = math.radians(a); c, si = math.cos(t), math.sin(t)
        xs = _carte_inverse(cx + c * (X - cx) + si * z, zb, w)
        im = cv2.remap(rgba, xs, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        im = cv2.resize(im, (lw, cote), interpolation=cv2.INTER_AREA) if s != 1 else im
        toile = np.zeros((cote, cote, 4), np.uint8)
        a0, a1 = max(0, x0), min(cote, x0 + lw)
        toile[:, a0:a1] = im[:, a0 - x0:a1 - x0]
        sortie.append((a, toile))
    return sortie


def webp(im: np.ndarray, qualite: int = 88) -> bytes:
    from PIL import Image
    b = io.BytesIO(); Image.fromarray(im, "RGBA").save(b, "WEBP", quality=qualite, method=4); return b.getvalue()
