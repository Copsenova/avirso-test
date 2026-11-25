"""Catalogue des coupes AVIRSO et consignes pour le modèle d'édition d'image (Qwen-Image-Edit-2511).

Les coupes sont décrites en texte par AVIRSO : aucune image de référence prise sur le web.
"""

COUPES: dict[str, str] = {
    "degrade": "a short low-fade haircut: very short sides blended into slightly longer textured hair on top, clean neat hairline",
    "court_boucle": "short natural curly hair, small tight curls about 3 cm long, rounded even shape",
    "court_lisse": "short straight hair, about 5 cm on top, neatly combed slightly to the side, short tapered sides",
    "afro": "a full rounded natural afro, dense coily hair about 12 cm long, even round volume",
    "tresses": "neat cornrow braids running straight back from the hairline to the nape, clean parts between the braids",
    "locks": "shoulder-length dreadlocks (locs), medium thickness, neat roots, falling naturally around the head",
    "mi_long": "chin-length straight hair with a center part, falling evenly on both sides of the face, ears partly covered",
    "long_lisse": "long straight hair reaching below the shoulders, center part, smooth and glossy",
    "long_boucle": "long curly hair reaching the shoulders, defined springy curls, voluminous",
}

COULEURS: dict[str, str] = {
    "noir": "natural black",
    "brun": "dark brown",
    "chatain": "medium chestnut brown",
    "blond": "natural dark blond",
    "roux": "natural copper red",
    "gris": "natural salt-and-pepper grey",
}

GARDE = ("keep the face, skin, beard, eyebrows, lighting and background unchanged; "
         "same person, same expression, same head pose, photorealistic, natural hair texture and hairline")


def consigne(coupe: str, couleur: str | None, vue: str) -> str:
    """Consigne anglaise pour une coupe, une couleur facultative et une vue ("face" ou "trois_quarts")."""
    if coupe not in COUPES:
        raise ValueError(f"coupe inconnue : {coupe}")
    if vue not in ("face", "trois_quarts"):
        raise ValueError(f"vue inconnue : {vue}")
    teinte = f", hair color {COULEURS[couleur]}" if couleur in COULEURS else ""
    if vue == "face":
        return f"Change only the hairstyle of the person to {COUPES[coupe]}{teinte}. {GARDE}."
    return (f"Change only the hairstyle of the person in image 1 to the same hairstyle as image 2 "
            f"({COUPES[coupe]}{teinte}), seen from this angle. {GARDE}.")
