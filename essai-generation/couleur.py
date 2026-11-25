"""Recalage de couleur : les images générées reprennent la teinte de peau de la vraie photo (espace Lab, moyenne et écart par canal)."""
import numpy as np, cv2


def stats_lab(img, masque):
    """Moyenne et écart-type Lab (OpenCV, 0-255) des pixels du masque. img : BGR ou BGRA uint8."""
    lab = cv2.cvtColor(np.ascontiguousarray(img[..., :3]), cv2.COLOR_BGR2LAB).astype(np.float32)
    p = lab[masque]
    if len(p) < 50:
        return None
    return p.mean(0), p.std(0) + 1e-3


def recaler(img, masque, cible, borne=(0.8, 1.25)):
    """Applique à toute l'image la correction qui amène les stats du masque sur `cible` (écart borné). Alpha conservé."""
    if cible is None:
        return img
    s = stats_lab(img, masque)
    if s is None:
        return img
    (m, e), (mc, ec) = s, cible
    k = np.clip(ec / e, *borne)
    lab = cv2.cvtColor(np.ascontiguousarray(img[..., :3]), cv2.COLOR_BGR2LAB).astype(np.float32)
    lab = np.clip((lab - m) * k + mc, 0, 255).astype(np.uint8)
    out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return np.dstack([out, img[..., 3]]) if img.shape[2] == 4 else out
