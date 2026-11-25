import pytest
from agents import nettoyer, PICTOGRAMMES
import agents

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


CAT_COMPLET = [{"id": i, "sujet": "peau", "titre": "t", "texte": "x", "niveau": "A"} for i in (1, 2)]


class _Rep:
    def __init__(self, texte, arret="end_turn"):
        self.stop_reason = arret
        self.content = [type("B", (), {"type": "text", "text": texte})()]


class _Client:
    """Faux client : enregistre les budgets demandés ; coupe toujours l'étape nommée dans `coupe`."""
    def __init__(self, coupe=None):
        self.budgets, self.coupe = [], coupe
        self.messages = self

    def create(self, model, max_tokens, system, messages, **k):
        etape = "analyste" if system == agents.CONSIGNE_ANALYSTE else "conseiller"
        self.budgets.append((etape, max_tokens))
        if etape == self.coupe:
            return _Rep("{", "max_tokens")
        if etape == "analyste":
            return _Rep('{"fiabilite": "bonne", "limites": []}')
        import json
        return _Rep(json.dumps(conseil()))


def test_budgets_avec_marge():
    c = _Client()
    agents.analyser(c, [], CAT_COMPLET)
    b = dict(c.budgets)
    assert b["analyste"] >= 4000 and b["conseiller"] >= 8000


def test_erreur_nomme_l_etape_coupee():
    c = _Client(coupe="conseiller")
    try:
        agents.analyser(c, [], CAT_COMPLET)
        assert False, "aurait dû échouer"
    except ValueError as e:
        assert "conseiller" in str(e)


def test_coupe_propre_titre_un_peu_long_garde():
    r = nettoyer(conseil(sujets=[sujet(0, titre="Protéger vos taches de soleil")] * 3), CAT)
    assert r["sujets"][0]["titre"] == "Protéger vos taches de soleil"


def test_coupe_propre_jamais_au_milieu():
    long = "Nettoyez avec un produit doux au plus deux fois par jour, puis hydratez avec un soin « non comédogène » (qui ne bouche pas les pores), matin et soir, sans frotter ni insister sur les zones sèches du visage."
    r = nettoyer(conseil(sujets=[sujet(0, action=long)] * 3), CAT)
    a = r["sujets"][0]["action"]
    assert a.endswith((".", "…")) and a.count("(") == a.count(")")
    assert not a.rstrip("…").split()[-1] in {"de", "les", "le", "la", "des", "du", "et", "à", "pas", "un", "une"}
