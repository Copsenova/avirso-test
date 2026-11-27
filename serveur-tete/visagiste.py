# Le visagiste : listes fermées dans lesquelles l'IA choisit coupe, couleur, barbe, monture, couleurs de vêtements et outils.
# Coupes, couleurs et barbes viennent du catalogue des styles (catalogue.json, celui de l'essai sur photo) ;
# montures, couleurs de vêtements et outils sont définis ici, avec les fiches sourcées de la bibliothèque (lot 10).

MONTURES = {
    "rectangulaire": "Rectangulaire", "carree": "Carrée", "ronde": "Ronde", "ovale": "Ovale", "aviateur": "Aviateur",
    "browline": "Browline (haut marqué)", "cat-eye": "Papillon (cat-eye)", "wayfarer": "Wayfarer", "geometrique": "Géométrique",
}
# couleurs de vêtements : nom et teinte affichée (pastille) ; la règle de choix est une pratique de métier (contraste, sous-ton)
VETEMENTS = {
    "blanc-pur": ("Blanc pur", "#FFFFFF"), "blanc-casse": ("Blanc cassé", "#F3EFE6"), "creme": ("Crème", "#EFE3C8"),
    "beige-sable": ("Beige sable", "#D8C3A0"), "camel": ("Camel", "#B9894F"), "chocolat": ("Chocolat", "#4E3426"),
    "gris-clair": ("Gris clair", "#C9CCCF"), "anthracite": ("Gris anthracite", "#3A3D42"), "noir": ("Noir", "#141414"),
    "marine": ("Bleu marine", "#1F2E4D"), "bleu-roi": ("Bleu roi", "#2E4FA8"), "bleu-ciel": ("Bleu ciel", "#9CC3E4"),
    "vert-olive": ("Vert olive", "#6B6B3A"), "vert-sapin": ("Vert sapin", "#1E4D3A"), "emeraude": ("Vert émeraude", "#13795B"),
    "bordeaux": ("Bordeaux", "#6D1F2E"), "rouge-brique": ("Rouge brique", "#A8442E"), "terracotta": ("Terracotta", "#C26A48"),
    "moutarde": ("Moutarde", "#C9A13A"), "rose-poudre": ("Rose poudré", "#E3B7B2"), "prune": ("Prune", "#5E2A4E"),
    "lavande": ("Lavande", "#B7A8D6"),
}
OUTILS = {
    "peigne-dents-larges": "Peigne à dents larges", "brosse-boucles": "Brosse souple à picots espacés (pour boucles)",
    "peigne-afro": "Peigne afro (pour soulever les racines)", "eponge-twists": "Éponge à twists",
    "brosse-sanglier-souple": "Brosse en poils de sanglier, souple", "brosse-sanglier-dure": "Brosse en poils de sanglier, dure",
    "durag": "Durag ou bonnet de compression", "bonnet-satin": "Bonnet ou taie en satin",
    "serviette-microfibre": "Serviette en microfibre (ou vieux t-shirt)", "diffuseur": "Diffuseur pour sèche-cheveux",
    "brosse-plate": "Brosse plate (paddle)", "brosse-barbe": "Brosse à barbe en poils de sanglier",
    "peigne-barbe": "Peigne à barbe", "tondeuse-sabots": "Tondeuse à sabots", "ciseaux-barbe": "Ciseaux de barbe",
}
AUCUNE = ("aucune", "Rasé de près ou sans barbe")
TEXTURES = {"raides": "lisse", "ondulés": "ondule", "bouclés": "boucle", "crépus": "crepu"}

S = {"type": "string"}
_obj = lambda props: {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
ENTIERS = {"type": "array", "items": {"type": "integer"}}


def _choix() -> dict:
    return _obj({"choix": S, "pourquoi": S, "autres": {"type": "array", "items": S}, "fiches": ENTIERS})


def schema(cat: dict) -> dict:
    """Schéma de sortie du bloc « visagiste ». Les listes fermées passent par le message (champ "listes") et non par le
    schéma : recopiées en « enum », elles rendaient la grammaire trop grosse pour l'API (vrai essai du 27/11).
    nettoyer_visagiste revérifie chaque identifiant."""
    return _obj({
        "coupe": _choix(), "couleur": _choix(), "barbe": _choix(), "lunettes": _choix(),
        "vetements": _obj({"couleurs": {"type": "array", "items": S}, "eviter": {"type": "array", "items": S}, "pourquoi": S, "fiches": ENTIERS}),
        "outils": {"type": "array", "items": _obj({"id": S, "pourquoi": S})},
    })


def listes_pour_le_modele(cat: dict) -> dict:
    """Ce que le conseiller reçoit pour choisir (identifiant, nom, et textures compatibles pour les coupes)."""
    return {"coupes": [{"id": c["id"], "nom": c["nom"], "famille": c.get("famille", ""), "textures": c.get("textures", [])} for c in cat["coupes"]],
            "couleurs": [{"id": c["id"], "nom": c["nom"]} for c in cat["couleurs"]],
            "barbes": [{"id": AUCUNE[0], "nom": AUCUNE[1]}] + [{"id": c["id"], "nom": c["nom"]} for c in cat["barbes"]],
            "montures": [{"id": k, "nom": n} for k, n in MONTURES.items()],
            "couleurs_vetements": [{"id": k, "nom": n} for k, (n, _) in VETEMENTS.items()],
            "outils": [{"id": k, "nom": n} for k, n in OUTILS.items()]}


def nettoyer_visagiste(b, cat: dict, fiches_ok: set, texture: str) -> dict | None:
    """Revérifie le bloc renvoyé par l'IA : identifiants connus, noms résolus, fiches du catalogue, coupes compatibles avec la texture."""
    if not isinstance(b, dict) or not b:
        return None
    court = lambda t, n=40: " ".join(str(t or "").split()[:n])
    fiches = lambda l: [int(i) for i in (l or []) if isinstance(i, int) and i in fiches_ok][:4]
    noms = {"coupe": {c["id"]: c for c in cat["coupes"]}, "couleur": {c["id"]: c for c in cat["couleurs"]},
            "barbe": {AUCUNE[0]: {"id": AUCUNE[0], "nom": AUCUNE[1]}, **{c["id"]: c for c in cat["barbes"]}},
            "lunettes": {k: {"id": k, "nom": n} for k, n in MONTURES.items()}}
    tex = TEXTURES.get(str(texture or "").strip().lower())
    out = {}
    for cle, table in noms.items():
        x = b.get(cle)
        if not isinstance(x, dict):
            continue
        ids = [i for i in [x.get("choix"), *(x.get("autres") or [])] if isinstance(i, str) and i in table]
        if cle == "coupe" and tex:      # une coupe pensée pour une autre texture de cheveux est écartée
            ids = [i for i in ids if not table[i].get("textures") or tex in table[i]["textures"]]
        ids = list(dict.fromkeys(ids))
        if not ids:
            continue
        out[cle] = {"id": ids[0], "nom": table[ids[0]]["nom"], "pourquoi": court(x.get("pourquoi")),
                    "autres": [{"id": i, "nom": table[i]["nom"]} for i in ids[1:3]], "fiches": fiches(x.get("fiches"))}
    vt = b.get("vetements")
    if isinstance(vt, dict):
        coul = [i for i in dict.fromkeys(vt.get("couleurs") or []) if i in VETEMENTS][:5]
        evit = [i for i in dict.fromkeys(vt.get("eviter") or []) if i in VETEMENTS and i not in coul][:2]
        if coul:
            out["vetements"] = {"couleurs": [{"id": i, "nom": VETEMENTS[i][0], "hex": VETEMENTS[i][1]} for i in coul],
                                "eviter": [{"id": i, "nom": VETEMENTS[i][0], "hex": VETEMENTS[i][1]} for i in evit],
                                "pourquoi": court(vt.get("pourquoi")), "fiches": fiches(vt.get("fiches"))}
    ou = [o for o in (b.get("outils") or []) if isinstance(o, dict) and o.get("id") in OUTILS]
    if ou:
        out["outils"] = [{"id": o["id"], "nom": OUTILS[o["id"]], "pourquoi": court(o.get("pourquoi"), 25)} for o in list({o["id"]: o for o in ou}.values())[:6]]
    return out or None
