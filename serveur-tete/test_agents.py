import pytest
from agents import nettoyer, PICTOGRAMMES

CAT = [{"id": 1}, {"id": 2}]
def sujet(i, **k):
    s = {"pictogramme": "peau", "titre": f"Sujet {i}", "constat": "On voit une peau lumineuse.", "consequence": "Elle capte la lumière.",
         "action": "Protégez-la chaque matin.", "zone": "cheeks", "fiches": [1], "produit": "spf50"}
    s.update(k); return s
def conseil(**k):
    c = {"accroche": "Vous cherchez à vous mettre en valeur au quotidien.", "sujets": [sujet(i) for i in range(3)], "suite": "Touchez vos joues.", "selection": [{"id": 1, "pourquoi": "x"}]}
    c.update(k); return c

def test_sujets_tronques_et_limites():
    r = nettoyer(conseil(sujets=[sujet(i, constat=" ".join(["mot"] * 60)) for i in range(7)]), CAT)
    assert len(r["sujets"]) == 5
    assert all(len(s["constat"].split()) <= 25 for s in r["sujets"])

def test_pictogramme_inconnu():
    r = nettoyer(conseil(sujets=[sujet(0, pictogramme="licorne")] + [sujet(i) for i in (1, 2)]), CAT)
    assert r["sujets"][0]["pictogramme"] == "visage" and "visage" in PICTOGRAMMES

def test_fiches_hors_catalogue_retirees():
    r = nettoyer(conseil(sujets=[sujet(0, fiches=[1, 99])] + [sujet(i) for i in (1, 2)]), CAT)
    assert r["sujets"][0]["fiches"] == [1]

def test_points_derives():
    r = nettoyer(conseil(), CAT)
    assert len(r["points"]) == len(r["sujets"]) and r["points"][0]["titre"] == "Sujet 0"

def test_accroche_vide_refusee():
    with pytest.raises(ValueError):
        nettoyer(conseil(accroche="  "), CAT)

def test_produit_vide_devient_none():
    r = nettoyer(conseil(sujets=[sujet(0, produit="")] + [sujet(i) for i in (1, 2)]), CAT)
    assert r["sujets"][0]["produit"] is None

def test_texte_de_compatibilite():
    r = nettoyer(conseil(), CAT)
    assert r["texte"].startswith("Vous cherchez") and len(r["texte"]) <= 400
