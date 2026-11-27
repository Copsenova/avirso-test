# Parcours visagiste guidé (lot 2, 26/11/2026) : le conseiller écrit les chapitres affichés par l'app
# (Ce que je vois → Ce que ça veut dire → Ce que je te conseille → Ta routine), au même format que la démo (lot1/web/src/apercu/chapitres.ts).
# Les choix viennent des listes fermées (coupes et barbes du catalogue, montures, couleurs de vêtements) ; tout est revérifié ici.
import visagiste

ORDRE = ["cheveux", "peau", "barbe", "regard", "lunettes", "couleurs"]
TABLE = {"cheveux": ("Cheveux", "cheveux", ["hair"]), "peau": ("Peau", "peau", ["cheeks"]), "barbe": ("Barbe", "barbe", ["chin", "jaw"]),
         "regard": ("Regard et sourcils", "yeux", ["eyes", "brows"]), "lunettes": ("Lunettes", "lunettes", ["eyes", "nose"]),
         "couleurs": ("Couleurs", "vetements", ["neck"])}
PICTOS = ["cheveux", "peau", "barbe", "yeux", "sourcils", "levres", "nez", "visage", "coupe", "couleur", "routine_jour", "routine_semaine",
          "produits", "soleil", "sommeil", "lunettes", "vetements", "outils", "alimentation"]
# clés des exemples de produits de l'app (lot1/web/src/accueil/exemplesProduits.json) : types sans marque
CLES = ["nettoyant", "ceramides", "spf50", "baume-spf", "baume-nuit", "huile", "bb-creme", "correcteur", "blush-creme", "enlumineur", "gel-sourcils",
        "crayon-sourcils", "fard-noisette", "liner-feutre", "mascara", "rouge-levres", "demaquillant", "shampoing", "apres-shampoing", "creme-coiffante",
        "peigne-dents-larges", "brosse-boucles", "eponge-twists", "brosse-sanglier-souple", "brosse-sanglier-dure", "durag", "bonnet-satin", "taie-satin",
        "serviette-microfibre", "diffuseur", "brosse-plate", "brosse-barbe", "peigne-barbe", "tondeuse-sabots"]
BARBE_VISIBLE = {"naissante", "courte", "moyenne", "longue"}

S = {"type": "string"}
_obj = lambda props: {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
_liste = lambda item: {"type": "array", "items": item}


def _listes(cat: dict) -> dict:
    """Identifiant → nom, pour les chapitres à liste fermée."""
    return {"cheveux": {c["id"]: c["nom"] for c in cat["coupes"]}, "barbe": {c["id"]: c["nom"] for c in cat["barbes"]},
            "lunettes": dict(visagiste.MONTURES), "couleurs": {k: n for k, (n, _) in visagiste.VETEMENTS.items()}}


def schema(cat: dict) -> dict:
    """Schéma strict du bloc « guide » : une liste de chapitres décrite UNE fois (le nom du chapitre est un champ).
    Pas d'« enum » : les listes fermées sont dans le message (champ « listes ») et revérifiées par nettoyer_guide ;
    recopiées dans le schéma, elles rendaient la grammaire trop grosse pour l'API (vrai essai du 27/11)."""
    choix = _obj({"id": S, "nom": S, "pourquoi": S})
    chapitre = _obj({"chapitre": S, "afficher": {"type": "boolean"}, "vu": _liste(_obj({"texte": S, "etiquette": S})), "sens": _liste(S),
                     "objectif": S, "premier": choix, "sur": choix, "audacieux": choix, "eviter": S,
                     "routine": _liste(_obj({"geste": S, "detail": S, "picto": S})), "produits": _liste(_obj({"type": S, "cle": S, "pourquoi": S}))})
    return _obj({"ouverture": _liste(S), "chapitres": _liste(chapitre)})


def schema_chapitre(cat: dict) -> dict:
    """Un seul chapitre : le guide part en un appel par chapitre, en parallèle (le guide entier prenait 188 s, vrai essai du 27/11)."""
    return _obj({"chapitre": schema(cat)["properties"]["chapitres"]["items"]})


SCHEMA_OUVERTURE = _obj({"ouverture": _liste(S)})


# Fiches utiles à chaque chapitre (sujets de savoir.json) : chaque appel du guide ne reçoit que les siennes.
SUJETS = {
    "cheveux": {"Outils selon le type de cheveux", "Cheveux crépus", "Coiffures protectrices", "Cheveux bouclés et crépus", "Coiffants homme",
                "Définir ses boucles", "Types de cheveux", "Coupe et forme du visage", "Dégradés (fade et taper)", "Locks", "Contours et line-up",
                "Cheveux et barbe blancs", "Couleur naturelle des cheveux", "Niveaux de couleur (coloration)", "Couleur de cheveux selon le sous-ton"},
    "peau": {"Actifs anti-acné", "Peaux foncées et noires", "Rétinoïdes et rétinol", "Maquillage des peaux foncées", "Carnations (échelles)", "Vitiligo",
             "Peau grasse", "Sous-tons et teint", "Écrans solaires", "Niacinamide", "Rougeurs et chaleur", "Vitamine C", "Acides exfoliants (AHA)",
             "Hydratation : les trois familles", "Albinisme", "Types de peau", "Peau sèche", "Taches de rousseur", "Bronzage et coups de soleil",
             "Combiner les actifs", "Poils incarnés"},
    "barbe": {"Poils incarnés", "Entretien de la barbe", "Contours et line-up", "Rasage", "Cheveux et barbe blancs", "Barbe selon la forme du visage",
              "Outils de la barbe"},
    "regard": {"Sourcils", "Faux cils", "Couleur des yeux", "Couleur des sourcils"},
    "lunettes": {"Taille de monture", "Forme de monture"},
    "couleurs": {"Couleurs des vêtements", "Sous-tons et teint", "Carnations (échelles)"},
}
LISTE_DU_CHAPITRE = {"cheveux": "coupes", "barbe": "barbes", "lunettes": "montures", "couleurs": "couleurs_vetements"}


def entree_du_chapitre(entree: dict, cid: str) -> dict:
    """Données d'un appel de chapitre : la description et les réponses, les fiches de son sujet (un sujet inconnu va partout
    plutôt que nulle part) et sa seule liste fermée (vrai essai du 27/11 : 373 000 jetons d'entrée en envoyant tout à chaque appel)."""
    connus = set().union(*SUJETS.values())
    cat = [f for f in entree.get("catalogue", []) if f.get("sujet") in SUJETS[cid] or f.get("sujet") not in connus]
    out = {"description": entree.get("description"), "reponses": entree.get("reponses", {}), "catalogue": cat}
    nom = LISTE_DU_CHAPITRE.get(cid)
    if nom and nom in (entree.get("listes") or {}):
        out["listes"] = {nom: entree["listes"][nom]}
    return out


def barbe_attendue(description: dict, reponses: dict | None) -> bool:
    """Chapitre barbe : seulement si une barbe se voit ou si la personne a choisi l'objectif « barbe »."""
    barbe = (description.get("barbe") or {}) if isinstance(description, dict) else {}
    presence = str(barbe.get("presence", "") if isinstance(barbe, dict) else "").strip().lower()
    return presence in BARBE_VISIBLE or "barbe" in ((reponses or {}).get("objectifs") or [])


CONSIGNE = f"""
4. Le bloc "guide" : le rendez-vous visagiste que la personne lira écran par écran, AU TUTOIEMENT (« je vois », « ton visage », « je te conseille »),
   comme un visagiste qui lui parle en face : phrases courtes, chaleureuses, un collégien doit comprendre, tout mot du métier expliqué.
   Limites strictes (au-delà, la phrase est coupée à l'affichage) : ouverture, "sens", "pourquoi" et "eviter" : 30 mots au plus par phrase ;
   "vu" : 25 mots au plus ; "objectif" et "detail" : 20 mots au plus ; "type" d'un produit : 8 mots au plus ; "geste" : 6 mots au plus.
   - "ouverture" : 3 phrases au plus, dans cet ordre : la forme de son visage, ses cheveux, sa peau et son sous-ton.
   - "chapitres" : une liste, un objet par chapitre, avec "chapitre" = cheveux, peau, barbe, regard (yeux et sourcils), lunettes ou
     couleurs (des vêtements), dans cet ordre. Pour chacun :
     "afficher" : false si la description ne donne pas assez de matière fiable ; "lunettes" s'affiche même si la personne ne porte pas de lunettes
       (le choix d'une monture, de vue ou de soleil, dépend de la forme du visage) ; pour "barbe", false si aucune barbe n'est visible
       et que la personne n'a pas choisi l'objectif « barbe » (tu ne devines jamais le genre).
     "vu" : 2 à 4 constats tirés de la description, rien d'inventé ; "etiquette" : 1 à 3 mots (ex. « Type 4A », « Dense »), ou "".
     "sens" : 1 à 3 phrases : ce que ça veut dire pour elle. "objectif" : une phrase.
     "premier", "sur", "audacieux" : mon premier choix, le choix sûr, le choix audacieux, trois propositions différentes, chacune avec
       son "pourquoi" (une phrase qui part de ce qu'on voit). Cheveux : coupes de la liste, compatibles avec sa texture (champ "textures") ;
       barbe : styles de la liste ; lunettes : montures de la liste ; couleurs : couleurs de vêtements de la liste — dans "id", recopie
       EXACTEMENT un identifiant du champ « listes » ("nom" : "") ; peau et regard : "nom" court, tiré des fiches choisies ("id" : "").
       "eviter" : une chose à éviter, avec la raison.
     "routine" : 3 ou 4 gestes, chacun avec sa fréquence dans "detail" et un "picto" parmi : {", ".join(PICTOS)} (ou "").
     "produits" : 1 à 4 types de produits (jamais de marque) ; pour "couleurs", des pièces de vêtement (ex. « Un haut vert olive ») ;
       pour "lunettes", la monture à essayer chez un opticien ; "cle" parmi : {", ".join(CLES)} (ou "") ;
       "pourquoi" : 20 mots au plus, la raison POUR CETTE PERSONNE, reliée à ce que tu as vu (ex. « Tes taches de rousseur foncent vite au soleil. »).
   Un savoir-faire ou une tendance n'est jamais présenté comme un fait prouvé. Aucune note de beauté, aucun défaut, aucun diagnostic.
"""


def _texte(t, n: int) -> str:
    """La consigne demande n mots ; on ne coupe qu'au-delà d'une marge (moitié en plus, 4 mots au moins) : un texte qui
    dépasse de peu reste entier plutôt que de finir par « … » (vrais essais du 27/11)."""
    from agents import borner      # import tardif : agents importe ce module
    return borner(t, n + max(4, n // 2)) if isinstance(t, str) else ""


def _etiquette(t) -> str:
    """Badge court : 4 mots au plus, sans la marge des phrases."""
    from agents import borner
    return borner(t, 4) if isinstance(t, str) else ""


class _Ecarte(Exception):
    """Raison (sans donnée personnelle) pour laquelle un chapitre n'est pas affiché."""


def _chapitre(cid: str, c, listes: dict, coupes: dict, tex: str | None) -> dict:
    if not isinstance(c, dict):
        raise _Ecarte("absent")
    if c.get("afficher") is not True:
        raise _Ecarte("afficher faux")
    vu = [{"texte": _texte(v.get("texte"), 25), **({"etiquette": e} if (e := _etiquette(v.get("etiquette"))) else {})}
          for v in (c.get("vu") or [])[:4] if isinstance(v, dict) and _texte(v.get("texte"), 25)]
    sens = [s for s in (_texte(x, 30) for x in (c.get("sens") or [])[:3]) if s]
    routine = [{"geste": _texte(g.get("geste"), 6), "detail": _texte(g.get("detail"), 20), **({"picto": g["picto"]} if g.get("picto") in PICTOS else {})}
               for g in (c.get("routine") or [])[:4] if isinstance(g, dict) and _texte(g.get("geste"), 6)]
    produits = [{"type": _texte(p.get("type"), 8), **({"cle": p["cle"]} if p.get("cle") in CLES else {}),
                 **({"pourquoi": w} if (w := _texte(p.get("pourquoi"), 20)) else {})}
                for p in (c.get("produits") or [])[:4] if isinstance(p, dict) and _texte(p.get("type"), 8)]
    conseils = {}
    for rang in ("premier", "sur", "audacieux"):
        x = c.get(rang)
        if not isinstance(x, dict) or not (pourquoi := _texte(x.get("pourquoi"), 30)):
            raise _Ecarte(f"{rang} : pourquoi manquant")
        if cid in listes:
            i = visagiste.resoudre(x.get("id"), listes[cid]) or visagiste.resoudre(x.get("nom"), listes[cid])
            if i is None:
                raise _Ecarte(f"{rang} : identifiant hors liste ({str(x.get('id'))[:30]!r}, nom {str(x.get('nom'))[:30]!r})")
            if cid == "cheveux" and tex and coupes[i].get("textures") and tex not in coupes[i]["textures"]:
                raise _Ecarte(f"{rang} : coupe incompatible avec la texture")
            conseils[rang] = {"id": i, "nom": listes[cid][i], "pourquoi": pourquoi, **({"essai": "coupe"} if cid == "cheveux" else {})}
        else:
            if not (nom := _texte(x.get("nom"), 8)):
                raise _Ecarte(f"{rang} : nom manquant")
            conseils[rang] = {"id": f"{cid}-{rang}", "nom": nom, "pourquoi": pourquoi}
    if len({k["nom"].lower() for k in conseils.values()}) < 3:
        raise _Ecarte("trois propositions non distinctes")
    if not (eviter := _texte(c.get("eviter"), 30)):
        raise _Ecarte("eviter manquant")
    objectif = _texte(c.get("objectif"), 20)
    if cid == "couleurs" and not produits:      # une palette n'a pas de produit de soin : les pièces viennent des couleurs choisies (liste fermée)
        produits = [{"type": f"Un vêtement {conseils[r]['nom'][:1].lower()}{conseils[r]['nom'][1:]}", "pourquoi": _texte(conseils[r]["pourquoi"], 20)}
                    for r in ("premier", "sur", "audacieux")]
    manque = [n for n, ok in (("vu", len(vu) >= 2), ("sens", sens), ("objectif", objectif), ("routine", len(routine) >= 3), ("produits", produits)) if not ok]
    if manque:
        raise _Ecarte("incomplet : " + ", ".join(manque))
    titre, picto, zones = TABLE[cid]
    return {"id": cid, "titre": titre, "picto": picto, "zones": zones, "vu": vu, "sens": sens, "objectif": objectif,
            "conseils": {**conseils, "eviter": eviter}, "routine": routine, "produits": produits}


def nettoyer_guide(b, cat: dict, description: dict, reponses: dict | None, echecs: dict | None = None) -> dict | None:
    """Revérifie le bloc « guide » : listes fermées, bornes, barbe seulement si visible ou demandée. None si rien d'affichable."""
    if isinstance(b, dict) and isinstance(b.get("chapitres"), list):      # forme du schéma : liste d'objets portant leur nom
        b = {**b, "chapitres": {c.get("chapitre"): c for c in b["chapitres"] if isinstance(c, dict) and isinstance(c.get("chapitre"), str)}}
    if not isinstance(b, dict) or not isinstance(b.get("chapitres"), dict) or not isinstance(b.get("ouverture"), list):
        return None
    phrases = [p for p in (_texte(x, 30) for x in b["ouverture"][:3]) if p]
    a_barbe = barbe_attendue(description, reponses)
    ch = (description.get("cheveux") or {}) if isinstance(description, dict) else {}
    tex = visagiste.TEXTURES.get(str(ch.get("texture", "") if isinstance(ch, dict) else "").strip().lower())
    listes, coupes = _listes(cat), {c["id"]: c for c in cat["coupes"]}
    chapitres, ecartes = [], {}
    for cid in ORDRE:
        if cid == "barbe" and not a_barbe:
            ecartes[cid] = "pas de barbe visible ni demandée"
            continue
        if cid in (echecs or {}):
            ecartes[cid] = f"appel en échec : {echecs[cid]}"
            continue
        try:
            chapitres.append(_chapitre(cid, b["chapitres"].get(cid), listes, coupes, tex))
        except _Ecarte as e:
            ecartes[cid] = str(e)
    if ecartes:
        print(f"chapitres écartés : {ecartes}", flush=True)
    if not phrases or not chapitres:
        return None
    return {"profil": {"barbe": a_barbe}, "ouverture": {"phrases": phrases}, "chapitres": chapitres, "ecartes": ecartes}
