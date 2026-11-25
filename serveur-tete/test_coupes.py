import pytest
from coupes import COUPES, COULEURS, consigne

GARDE = "keep the face, skin, beard, eyebrows, lighting and background unchanged"


def test_consigne_garde_identite():
    assert GARDE in consigne("afro", None, "face")


def test_consigne_trois_quarts_reference():
    assert "same hairstyle as image 2" in consigne("afro", "noir", "trois_quarts")


def test_coupe_inconnue():
    with pytest.raises(ValueError):
        consigne("xyz", None, "face")


def test_catalogue():
    assert set(COUPES) >= {"degrade", "court_boucle", "afro", "tresses", "locks", "mi_long", "long_lisse", "long_boucle"}


def test_couleur_ajoutee():
    assert COULEURS["chatain"] in consigne("degrade", "chatain", "face")


def test_valider_demande():
    from coupes import valider_demande
    assert valider_demande("afro", "noir") == ("afro", "noir")
    assert valider_demande("afro", "violet") == ("afro", None)
    assert valider_demande("afro", "") == ("afro", None)
    with pytest.raises(ValueError):
        valider_demande("perruque", "noir")
