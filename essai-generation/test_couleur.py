import numpy as np, cv2
from couleur import stats_lab, recaler


def _peau(teinte):
    rng = np.random.default_rng(0)
    im = np.clip(np.array(teinte, np.float32) + rng.normal(0, 6, (64, 64, 3)), 0, 255).astype(np.uint8)
    return im


def test_recaler_ramene_la_teinte():
    ref = _peau((90, 120, 170))            # BGR peau
    derive = _peau((120, 110, 170))        # même peau tirée vers le bleu
    m = np.ones((64, 64), bool)
    cible = stats_lab(ref, m)
    out = recaler(derive, m, cible)
    d = np.abs(stats_lab(out, m)[0] - cible[0]).max()
    assert d < 1.0


def test_masque_vide_ne_change_rien():
    im = _peau((90, 120, 170))
    assert np.array_equal(recaler(im, np.zeros((64, 64), bool), stats_lab(im, np.ones((64, 64), bool))), im)


def test_garde_la_transparence():
    im = np.dstack([_peau((90, 120, 170)), np.full((64, 64), 77, np.uint8)])
    out = recaler(im, np.ones((64, 64), bool), stats_lab(_peau((80, 110, 160)), np.ones((64, 64), bool)))
    assert out.shape == (64, 64, 4) and (out[..., 3] == 77).all()
