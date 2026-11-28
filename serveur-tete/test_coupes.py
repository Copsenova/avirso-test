import pytest
from coupes import COUPES, COULEURS, BARBES, consigne, valider_demande

GARDE = "keep the face, skin, eyebrows, lighting and background unchanged"


def test_catalogue_complet():
    assert len(COUPES) >= 140 and len(BARBES) >= 30 and len(COULEURS) >= 40
    assert {"twists", "locks", "tresses", "afro", "degrade", "senegalese_twists"} <= set(COUPES)


def test_consigne_garde_identite():
    assert GARDE in consigne("afro", None, "face")


def test_consigne_trois_quarts_sans_reference():
    t = consigne("afro", "noir", "trois_quarts")
    assert "image 2" not in t and "keep the same three-quarter head angle" in t


def test_couleur_ajoutee():
    assert COULEURS["chatain"] in consigne("degrade", "chatain", "face")


def test_barbe_seule():
    t = consigne(None, None, "face", barbe="barbe_courte", texture_barbe="crepue", couleur_barbe="blanc")
    assert BARBES["barbe_courte"] in t and "white" in t and "kinky" in t and "hairstyle" not in t.split(".")[0]


def test_barbe_et_coupe():
    t = consigne("twists", "noir", "face", barbe="bouc")
    assert COUPES["twists"] in t and BARBES["bouc"] in t
    assert "beard" not in GARDE.split(";")[0] or True


def test_sans_barbe_demandee_la_barbe_reste():
    assert "keep the beard unchanged" in consigne("afro", None, "face")


def test_rien_demande():
    with pytest.raises(ValueError):
        consigne(None, None, "face")


def test_coupe_inconnue():
    with pytest.raises(ValueError):
        consigne("xyz", None, "face")


def test_valider_demande():
    assert valider_demande("afro", "noir") == ("afro", "noir")
    assert valider_demande("afro", "violetfoncé") == ("afro", None)
    assert valider_demande("", "") == (None, None)
    with pytest.raises(ValueError):
        valider_demande("perruque", "noir")


def test_lunettes_ajoutees():
    # 28/11 : l'agent propose des montures ; elles doivent pouvoir s'essayer comme les coupes
    import coupes as c
    t = c.consigne(None, None, "face", lunettes="rectangulaire")
    assert "eyeglasses" in t and "rectangular" in t and "keep the hair unchanged" in t
    assert set(c.LUNETTES) >= {"rectangulaire", "wayfarer", "cat-eye", "ronde", "ovale", "browline", "aviateur", "carree", "geometrique"}


def test_lunettes_seules_suffisent_et_inconnues_refusees():
    import coupes as c
    c.consigne(None, None, "trois_quarts", lunettes="wayfarer")
    import pytest
    with pytest.raises(ValueError):
        c.consigne(None, None, "face", lunettes="monocle")
