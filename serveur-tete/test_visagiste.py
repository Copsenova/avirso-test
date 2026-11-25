import visagiste as v

FICHES = {730, 731, 745}


def bloc(**k):
    b = {
        "coupe": {"choix": "taper_twists", "pourquoi": "Vos boucles serrées tiennent bien en twists.", "autres": ["afro_court", "inconnue"], "fiches": [730, 9999]},
        "couleur": {"choix": "noir", "pourquoi": "Proche de votre couleur naturelle.", "autres": [], "fiches": []},
        "barbe": {"choix": "aucune", "pourquoi": "Vous êtes rasé de près.", "autres": ["barbe_courte"], "fiches": []},
        "lunettes": {"choix": "rectangulaire", "pourquoi": "Visage rond.", "autres": ["ronde", "pas-une-forme"], "fiches": []},
        "vetements": {"couleurs": ["marine", "camel", "fuchsia-fluo"], "eviter": ["noir"], "pourquoi": "Contraste fort.", "fiches": [745]},
        "outils": [{"id": "eponge-twists", "pourquoi": "Pour former les twists."}, {"id": "lisseur-magique", "pourquoi": "x"}],
    }
    b.update(k); return b


CAT = {"coupes": [{"id": "taper_twists", "nom": "Taper avec twists", "textures": ["crepu", "boucle"]}, {"id": "afro_court", "nom": "Afro court", "textures": ["crepu"]},
                  {"id": "raie_lisse", "nom": "Raie sur le côté", "textures": ["lisse"]}],
       "couleurs": [{"id": "noir", "nom": "Noir naturel"}], "barbes": [{"id": "barbe_courte", "nom": "Barbe courte"}]}


def test_ids_inconnus_retires_et_noms_resolus():
    r = v.nettoyer_visagiste(bloc(), CAT, FICHES, "crépus")
    assert r["coupe"]["id"] == "taper_twists" and r["coupe"]["nom"] == "Taper avec twists"
    assert [a["id"] for a in r["coupe"]["autres"]] == ["afro_court"]
    assert r["coupe"]["fiches"] == [730]
    assert [m["id"] for m in r["lunettes"]["autres"]] == ["ronde"]
    assert [c["id"] for c in r["vetements"]["couleurs"]] == ["marine", "camel"]
    assert all(c["hex"].startswith("#") for c in r["vetements"]["couleurs"])
    assert [o["id"] for o in r["outils"]] == ["eponge-twists"]


def test_barbe_aucune_gardee():
    r = v.nettoyer_visagiste(bloc(), CAT, FICHES, "crépus")
    assert r["barbe"]["id"] == "aucune" and r["barbe"]["nom"]


def test_coupe_incompatible_avec_la_texture_ecartee():
    r = v.nettoyer_visagiste(bloc(coupe={"choix": "raie_lisse", "pourquoi": "x", "autres": ["afro_court"], "fiches": []}), CAT, FICHES, "crépus")
    assert r["coupe"]["id"] == "afro_court"          # l'option compatible remonte en premier choix


def test_texture_indeterminee_ne_filtre_pas():
    r = v.nettoyer_visagiste(bloc(coupe={"choix": "raie_lisse", "pourquoi": "x", "autres": [], "fiches": []}), CAT, FICHES, "indéterminé")
    assert r["coupe"]["id"] == "raie_lisse"


def test_schema_contraint_par_listes():
    s = v.schema(CAT)
    assert s["properties"]["coupe"]["properties"]["choix"]["enum"] == ["taper_twists", "afro_court", "raie_lisse"]
    assert "aucune" in s["properties"]["barbe"]["properties"]["choix"]["enum"]
    assert set(s["properties"]["outils"]["items"]["properties"]["id"]["enum"]) == set(v.OUTILS)


def test_bloc_absent_ou_vide():
    assert v.nettoyer_visagiste(None, CAT, FICHES, "crépus") is None
    assert v.nettoyer_visagiste({}, CAT, FICHES, "crépus") is None
