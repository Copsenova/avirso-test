import copy, json, os
import chapitres

CAT = json.load(open(os.path.join(os.path.dirname(__file__), "catalogue.json"), encoding="utf-8"))
IDS = ["cheveux", "peau", "barbe", "regard", "lunettes", "couleurs"]


def chap(premier, sur, audacieux):
    return {"afficher": True,
            "vu": [{"texte": "Je vois des cheveux denses et brillants.", "etiquette": "Dense"}, {"texte": "La longueur arrive aux épaules.", "etiquette": ""}],
            "sens": ["Ta densité permet une coupe structurée."], "objectif": "Garder du volume sans effort.",
            "premier": premier, "sur": sur, "audacieux": audacieux, "eviter": "Le lissage quotidien à haute température.",
            "routine": [{"geste": "Lave deux fois par semaine", "detail": "Shampoing doux.", "picto": "cheveux"},
                        {"geste": "Démêle sur cheveux mouillés", "detail": "Peigne à dents larges.", "picto": "outils"},
                        {"geste": "Dors sur du satin", "detail": "Taie en satin.", "picto": "sommeil"}],
            "produits": [{"type": "Shampoing doux", "cle": "shampoing"}]}


def libre(n):
    return {"nom": n, "pourquoi": "Il répond à ce que je vois sur ta peau."}


def ferme(i):
    return {"id": i, "pourquoi": "Il répond à ce que je vois sur toi."}


def bloc():
    return {"ouverture": ["Ton visage est ovale.", "Tes cheveux sont lisses.", "Ta peau est claire, sous-ton froid."],
            "chapitres": {"cheveux": chap(ferme("carre_long"), ferme("mi_long_degrade"), ferme("carre_frange")),
                          "peau": chap(libre("SPF chaque matin"), libre("Routine en trois gestes"), libre("Teint léger")),
                          "barbe": chap(ferme("barbe_courte"), ferme("trois_jours"), ferme("barbe_moyenne")),
                          "regard": chap(libre("Gel à sourcils"), libre("Mascara brun"), libre("Liner étiré")),
                          "lunettes": chap(ferme("wayfarer"), ferme("rectangulaire"), ferme("cat-eye")),
                          "couleurs": chap(ferme("vert-olive"), ferme("marine"), ferme("bordeaux"))}}


def desc(barbe="courte", texture="raides"):
    return {"cheveux": {"texture": texture}, "barbe": {"presence": barbe}}


def test_guide_complet():
    g = chapitres.nettoyer_guide(bloc(), CAT, desc(), None)
    assert [c["id"] for c in g["chapitres"]] == IDS
    assert g["profil"] == {"barbe": True}
    lun = next(c for c in g["chapitres"] if c["id"] == "lunettes")
    assert lun["conseils"]["premier"]["nom"] == "Wayfarer" and lun["titre"] == "Lunettes" and lun["zones"] == ["eyes", "nose"]
    ch = g["chapitres"][0]
    assert ch["conseils"]["premier"]["essai"] == "coupe" and ch["conseils"]["premier"]["id"] == "carre_long"
    assert ch["picto"] == "cheveux" and ch["conseils"]["eviter"]
    assert g["ouverture"]["phrases"][0] == "Ton visage est ovale."


def test_barbe_retiree_sans_barbe_visible():
    g = chapitres.nettoyer_guide(bloc(), CAT, desc("aucune"), {"objectifs": []})
    assert "barbe" not in [c["id"] for c in g["chapitres"]] and g["profil"]["barbe"] is False


def test_barbe_gardee_si_objectif_barbe():
    g = chapitres.nettoyer_guide(bloc(), CAT, desc("indéterminé"), {"objectifs": ["barbe"]})
    assert "barbe" in [c["id"] for c in g["chapitres"]]


def test_identifiant_inconnu_retire_le_chapitre():
    b = bloc(); b["chapitres"]["lunettes"]["premier"]["id"] = "licorne"
    ids = [c["id"] for c in chapitres.nettoyer_guide(b, CAT, desc(), None)["chapitres"]]
    assert "lunettes" not in ids and "couleurs" in ids


def test_choix_en_double_retire_le_chapitre():
    b = bloc(); b["chapitres"]["couleurs"]["sur"]["id"] = "vert-olive"
    assert "couleurs" not in [c["id"] for c in chapitres.nettoyer_guide(b, CAT, desc(), None)["chapitres"]]


def test_coupe_incompatible_avec_la_texture():
    b = bloc(); b["chapitres"]["cheveux"]["premier"]["id"] = "ivy_league"      # lisse et ondulé seulement
    assert "cheveux" not in [c["id"] for c in chapitres.nettoyer_guide(b, CAT, desc(texture="crépus"), None)["chapitres"]]


def test_afficher_faux():
    b = bloc(); b["chapitres"]["peau"]["afficher"] = False
    assert "peau" not in [c["id"] for c in chapitres.nettoyer_guide(b, CAT, desc(), None)["chapitres"]]


def test_bornes():
    b = bloc(); p = b["chapitres"]["peau"]
    p["vu"] = [{"texte": " ".join(["mot"] * 60), "etiquette": "a b c d e"}] * 6
    p["routine"] = p["routine"] * 2
    g = chapitres.nettoyer_guide(b, CAT, desc(), None)
    peau = next(c for c in g["chapitres"] if c["id"] == "peau")
    assert len(peau["vu"]) == 4 and len(peau["vu"][0]["texte"].split()) <= 37 and len(peau["vu"][0]["etiquette"].split()) <= 4
    assert len(peau["routine"]) == 4
    b2 = bloc(); b2["chapitres"]["peau"]["routine"] = b2["chapitres"]["peau"]["routine"][:2]
    assert "peau" not in [c["id"] for c in chapitres.nettoyer_guide(b2, CAT, desc(), None)["chapitres"]]


def test_cle_et_picto_hors_liste():
    b = bloc(); c = b["chapitres"]["peau"]
    c["produits"] = [{"type": "Crème", "cle": "marque-x"}]; c["routine"][0]["picto"] = "licorne"
    peau = next(x for x in chapitres.nettoyer_guide(b, CAT, desc(), None)["chapitres"] if x["id"] == "peau")
    assert peau["produits"] == [{"type": "Crème"}] and "picto" not in peau["routine"][0]


def test_aucun_chapitre_valide():
    b = bloc()
    for c in b["chapitres"].values():
        c["afficher"] = False
    assert chapitres.nettoyer_guide(b, CAT, desc(), None) is None


def test_ouverture_vide():
    b = bloc(); b["ouverture"] = ["  "]
    assert chapitres.nettoyer_guide(b, CAT, desc(), None) is None


def test_entree_invalide():
    assert chapitres.nettoyer_guide(None, CAT, desc(), None) is None
    assert chapitres.nettoyer_guide({"ouverture": "x"}, CAT, desc(), None) is None


def test_schema_strict():
    s = chapitres.schema(CAT)

    def parcours(n):
        if isinstance(n, dict):
            if n.get("type") == "object":
                assert n.get("additionalProperties") is False and set(n["required"]) == set(n["properties"])
            for v in n.values():
                parcours(v)
        elif isinstance(n, list):
            for v in n:
                parcours(v)
    parcours(s)
    # le schéma reste petit : les listes fermées sont dans le message (champ « listes ») et revérifiées par nettoyer_guide,
    # pas recopiées dans le schéma (sinon l'API refuse une grammaire trop grosse — vrai essai du 27/11)
    import json as _json
    assert "enum" not in _json.dumps(s)
    assert len(_json.dumps(s)) < 4000
    assert all(p in chapitres.CONSIGNE for p in chapitres.PICTOS) and all(k in chapitres.CONSIGNE for k in chapitres.CLES)
    assert "nom" in s["properties"]["chapitres"]["items"]["properties"]["premier"]["properties"]


def test_chapitres_en_liste():
    # forme renvoyée par l'IA depuis le 27/11 : une liste d'objets « chapitre », décrite une seule fois dans le schéma
    b = bloc()
    liste = []
    for cid, c in b["chapitres"].items():
        x = copy.deepcopy(c); x["chapitre"] = cid
        for rang in ("premier", "sur", "audacieux"):
            x[rang] = {"id": x[rang].get("id", ""), "nom": x[rang].get("nom", ""), "pourquoi": x[rang]["pourquoi"]}
        liste.append(x)
    b["chapitres"] = liste
    g = chapitres.nettoyer_guide(b, CAT, desc(), None)
    assert [c["id"] for c in g["chapitres"]] == IDS
    s = chapitres.schema(CAT)["properties"]["chapitres"]
    assert s["type"] == "array" and "chapitre" in s["items"]["properties"]


def test_identifiant_donne_par_son_nom():
    # sans « enum » dans le schéma, le modèle peut renvoyer le nom affiché (« Bleu marine ») au lieu de l'identifiant
    b = bloc()
    b["chapitres"]["couleurs"] = chap(ferme("Bleu marine"), ferme("vert-olive"), ferme("BORDEAUX"))
    r = chapitres.nettoyer_guide(b, CAT, {"barbe": {"presence": "aucune"}}, None)
    c = next(x for x in r["chapitres"] if x["id"] == "couleurs")
    assert [c["conseils"][k]["id"] for k in ("premier", "sur", "audacieux")] == ["marine", "vert-olive", "bordeaux"]


def test_identifiant_inconnu_reste_refuse():
    b = bloc()
    b["chapitres"]["couleurs"] = chap(ferme("Fuchsia fluo"), ferme("vert-olive"), ferme("bordeaux"))
    r = chapitres.nettoyer_guide(b, CAT, {"barbe": {"presence": "aucune"}}, None)
    assert "couleurs" not in [x["id"] for x in r["chapitres"]]


def test_consigne_donne_les_limites_de_mots():
    # vrai essai du 27/11 : des phrases trop longues finissaient coupées par « … » au nettoyage
    for limite in ("30 mots", "25 mots", "20 mots", "8 mots", "6 mots"):
        assert limite in chapitres.CONSIGNE


def test_chapitre_ecarte_donne_sa_raison():
    # vrai essai du 27/11 : lunettes et couleurs écartées sans qu'on sache pourquoi
    b = bloc()
    b["chapitres"]["couleurs"] = chap(ferme("Fuchsia fluo"), ferme("vert-olive"), ferme("bordeaux"))
    b["chapitres"]["lunettes"] = {**b["chapitres"]["lunettes"], "afficher": False}
    r = chapitres.nettoyer_guide(b, CAT, {"barbe": {"presence": "aucune"}}, None)
    assert r["ecartes"]["couleurs"].startswith("premier : identifiant hors liste")
    assert r["ecartes"]["lunettes"] == "afficher faux"
    assert "barbe" in r["ecartes"]


def test_couleurs_sans_produits_garde_le_chapitre():
    # vrai essai du 27/11 : « couleurs » écarté (incomplet : produits) ; une palette n'a pas de produit au sens soin
    b = bloc()
    b["chapitres"]["couleurs"] = {**chap(ferme("marine"), ferme("vert-olive"), ferme("bordeaux")), "produits": []}
    r = chapitres.nettoyer_guide(b, CAT, {"barbe": {"presence": "aucune"}}, None)
    c = next(x for x in r["chapitres"] if x["id"] == "couleurs")
    assert [p["type"] for p in c["produits"]] == ["Un vêtement bleu marine", "Un vêtement vert olive", "Un vêtement bordeaux"]


def test_consigne_lunettes_meme_sans_lunettes_portees():
    assert "même si la personne ne porte pas de lunettes" in chapitres.CONSIGNE
    assert "Un haut vert olive" in chapitres.CONSIGNE


def test_marge_avant_de_couper():
    # vrais essais du 27/11 : 3 à 4 textes coupés par « … » à chaque analyse, pour quelques mots de trop
    assert chapitres._texte("Laver toutes les 2 à 3 semaines", 6) == "Laver toutes les 2 à 3 semaines"   # 7 mots pour 6 demandés
    long = " ".join(["mot"] * 40)
    assert len(chapitres._texte(long, 20).split()) <= 30                                           # au-delà de la marge, on coupe
