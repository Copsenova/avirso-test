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


STYLES = {"coupes": [{"id": "afro_court", "nom": "Afro court", "textures": ["crepu"]}], "couleurs": [{"id": "noir", "nom": "Noir naturel"}], "barbes": [{"id": "barbe_courte", "nom": "Barbe courte"}]}


class _ClientVisagiste(_Client):
    def create(self, model, max_tokens, system, messages, **k):
        self.schemas = getattr(self, "schemas", []) + [k.get("extra_body", {}).get("output_config", {}).get("format", {}).get("schema")]
        if system == agents.CONSIGNE_ANALYSTE:
            return _Rep('{"fiabilite": "bonne", "limites": [], "cheveux": {"texture": "crépus"}}')
        import json
        self.demande = messages[0]["content"][0]["text"]
        c = conseil(visagiste={"coupe": {"choix": "afro_court", "pourquoi": "Vos boucles serrées.", "autres": [], "fiches": [1]},
                               "outils": [{"id": "eponge-twists", "pourquoi": "Pour définir."}]})
        return _Rep(json.dumps(c))


def test_visagiste_dans_la_reponse():
    c = _ClientVisagiste()
    r = agents.analyser(c, [], CAT_COMPLET, styles=STYLES)
    assert r["visagiste"]["coupe"]["nom"] == "Afro court"
    assert r["visagiste"]["outils"][0]["id"] == "eponge-twists"
    assert any(s and "visagiste" in s["properties"] for s in c.schemas)      # appels parallèles : ordre non garanti
    assert "afro_court" in c.demande          # le conseiller reçoit les listes où choisir


def test_sans_styles_pas_de_bloc_visagiste():
    c = _Client()
    r = agents.analyser(c, [], CAT_COMPLET)
    assert r.get("visagiste") is None


class _ClientGuide(_Client):
    """Analyste : pas de barbe, cheveux raides ; conseiller : visagiste + guide complet (6 chapitres dont barbe)."""
    def create(self, model, max_tokens, system, messages, **k):
        import threading
        with getattr(self, "_verrou", threading.Lock()):
            schema = k.get("extra_body", {}).get("output_config", {}).get("format", {}).get("schema")
            self.appels = getattr(self, "appels", []) + [(system, schema, max_tokens)]
            self.budgets.append(max_tokens)
        if system == agents.CONSIGNE_ANALYSTE:
            return _Rep('{"fiabilite": "bonne", "limites": [], "cheveux": {"texture": "raides"}, "barbe": {"presence": "aucune"}}')
        import json, test_chapitres
        return _Rep(json.dumps(conseil(visagiste={}, guide=test_chapitres.bloc())))


def _appel_guide(c):
    return [a for a in c.appels if a[1] and "guide" in a[1]["properties"]]


def test_analyser_renvoie_le_guide():
    import test_chapitres
    c = _ClientGuide()
    r = agents.analyser(c, [], CAT_COMPLET, None, styles=test_chapitres.CAT)
    ids = [x["id"] for x in r["guide"]["chapitres"]]
    assert ids == ["cheveux", "peau", "regard", "lunettes", "couleurs"]      # pas de barbe visible
    (systeme, schema, budget), = _appel_guide(c)
    assert schema["required"] == ["guide"]
    assert "TUTOIEMENT" in systeme and budget >= 10000


def test_guide_dans_un_appel_separe():
    # l'API refuse conseiller + visagiste + guide dans un seul schéma (« compiled grammar is too large », vrai essai du 27/11)
    import test_chapitres
    c = _ClientGuide()
    agents.analyser(c, [], CAT_COMPLET, None, styles=test_chapitres.CAT)
    for _, schema, _ in c.appels:
        if schema:
            assert not ({"visagiste", "guide"} <= set(schema["properties"]))
    assert any(s and "visagiste" in s["properties"] for _, s, _ in c.appels)


def test_guide_en_echec_ne_bloque_pas_l_analyse():
    import test_chapitres

    class C(_ClientGuide):
        def create(self, model, max_tokens, system, messages, **k):
            s = k.get("extra_body", {}).get("output_config", {}).get("format", {}).get("schema")
            if s and "guide" in s["properties"]:
                raise RuntimeError("panne du guide")
            return super().create(model, max_tokens, system, messages, **k)
    r = agents.analyser(C(), [], CAT_COMPLET, None, styles=test_chapitres.CAT)
    assert r["ok"] is True and r["guide"] is None and r["accroche"]
    assert r["guide_erreur"].startswith("RuntimeError")      # diagnostic sans donnée personnelle


def test_guide_rejete_au_nettoyage_est_signale():
    import json

    class C(_ClientGuide):
        def create(self, model, max_tokens, system, messages, **k):
            if system == agents.CONSIGNE_ANALYSTE:
                return _Rep('{"fiabilite": "bonne", "limites": []}')
            return _Rep(json.dumps(conseil(visagiste={}, guide={"ouverture": [], "chapitres": []})))
    r = agents.analyser(C(), [], CAT_COMPLET, None, styles=STYLES)
    assert r["guide"] is None and r["guide_erreur"] == "rejeté au nettoyage"


def test_guide_invalide_donne_none():
    import json

    class C(_ClientGuide):
        def create(self, model, max_tokens, system, messages, **k):
            if system == agents.CONSIGNE_ANALYSTE:
                return _Rep('{"fiabilite": "bonne", "limites": []}')
            return _Rep(json.dumps(conseil(visagiste={}, guide={"ouverture": [], "chapitres": {}})))
    r = agents.analyser(C(), [], CAT_COMPLET, None, styles=STYLES)
    assert r["guide"] is None and r["ok"] is True


def test_temps_par_etape():
    import test_chapitres
    r = agents.analyser(_ClientGuide(), [], CAT_COMPLET, None, styles=test_chapitres.CAT)
    assert set(r["temps"]) == {"analyste", "conseiller", "guide"} and all(isinstance(v, float) for v in r["temps"].values())
