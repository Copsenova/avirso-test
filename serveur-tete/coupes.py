"""Catalogue des styles AVIRSO et consignes pour le modèle d'édition d'image (Qwen-Image-Edit-2511).

Le catalogue vient du deuxième cerveau (AVIRSO-cerveau, `python3 construire.py catalogue` → catalogue.json) :
coupes du monde entier, couleurs et teintures, barbes (styles, textures, couleurs). Aucune image de référence prise sur le web.
"""
import json, os

_K = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalogue.json"), encoding="utf-8"))
COUPES: dict[str, str] = {e["id"]: e["description"] for e in _K["coupes"]}
COULEURS: dict[str, str] = {e["id"]: e["description"] for e in _K["couleurs"]}
BARBES: dict[str, str] = {e["id"]: e["description"] for e in _K["barbes"]}
TEXTURES_BARBE: dict[str, str] = {e["id"]: e["description"] for e in _K["textures_barbe"]}
COULEURS_BARBE: dict[str, str] = {e["id"]: e["description"] for e in _K["couleurs_barbe"]}

# montures proposées par le visagiste (visagiste.MONTURES) : description pour le modèle d'image
LUNETTES: dict[str, str] = {
    "rectangulaire": "rectangular", "carree": "square", "ronde": "round", "ovale": "oval", "aviateur": "aviator-style",
    "browline": "browline (bold upper rim, thin lower rim)", "cat-eye": "cat-eye", "wayfarer": "wayfarer-style", "geometrique": "geometric hexagonal",
}

GARDE = ("keep the face, skin, eyebrows, lighting and background unchanged; "
         "same person, same expression, photorealistic, natural texture")


def consigne(coupe: str | None, couleur: str | None, vue: str, barbe: str | None = None,
             texture_barbe: str | None = None, couleur_barbe: str | None = None, lunettes: str | None = None) -> str:
    """Consigne anglaise. vue : "face" ou "trois_quarts" (chaque photo est retouchée seule, sans image de référence)."""
    if coupe is not None and coupe not in COUPES:
        raise ValueError(f"coupe inconnue : {coupe}")
    if barbe is not None and barbe not in BARBES:
        raise ValueError(f"barbe inconnue : {barbe}")
    if lunettes is not None and lunettes not in LUNETTES:
        raise ValueError(f"monture inconnue : {lunettes}")
    if coupe is None and barbe is None and couleur is None and couleur_barbe is None and texture_barbe is None and lunettes is None:
        raise ValueError("rien à changer")
    if vue not in ("face", "trois_quarts"):
        raise ValueError(f"vue inconnue : {vue}")
    changer, garder = [], [GARDE]
    teinte = COULEURS.get(couleur) if couleur else None
    if coupe:
        changer.append(f"change the hairstyle to {COUPES[coupe]}" + (f", hair color {teinte}" if teinte else ""))
    elif teinte:
        changer.append(f"keep the same haircut but dye the hair {teinte}")
    else:
        garder.append("keep the hair unchanged")
    if barbe or texture_barbe in TEXTURES_BARBE or couleur_barbe in COULEURS_BARBE:
        style = BARBES[barbe] if barbe else "the same beard shape"
        tx = f", {TEXTURES_BARBE[texture_barbe]}" if texture_barbe in TEXTURES_BARBE else ""
        cb = f", beard color {COULEURS_BARBE[couleur_barbe]}" if couleur_barbe in COULEURS_BARBE else ""
        changer.append(f"change the facial hair to {style}{tx}{cb}")
    else:
        garder.append("keep the facial hair exactly as it is, do not add or remove any facial hair")
    if lunettes:
        changer.append(f"add a pair of {LUNETTES[lunettes]} eyeglasses with thin frames and clear lenses, resting naturally on the nose")
    angle = "keep the same three-quarter head angle and pose as the photo" if vue == "trois_quarts" else "keep the same head pose"
    texte = " and ".join(changer)
    return f"{texte[0].upper()}{texte[1:]}. {'; '.join(garder)}; {angle}."


def valider_demande(coupe: str | None, couleur: str | None) -> tuple[str | None, str | None]:
    """Contrôle une demande venue de l'app : coupe du catalogue (ou aucune), couleur hors nuancier ignorée."""
    coupe = coupe or None
    if coupe is not None and coupe not in COUPES:
        raise ValueError(f"coupe inconnue : {coupe}")
    return coupe, (couleur if couleur in COULEURS else None)
