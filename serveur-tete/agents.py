# AVIRSO — agents d'analyse (24/11/2026).
#
# 1. L'analyste regarde les photos et décrit l'apparence en mots simples (cheveux, barbe, peau, sourcils, visage).
#    Il dit quand il ne voit pas bien. Il ne note pas la beauté, ne devine ni l'origine, ni l'âge, ni une maladie.
# 2. Le chercheur et le conseiller (un seul appel, sans les photos) reçoivent cette description et le catalogue des fiches
#    sourcées de la bibliothèque AVIRSO ; ils choisissent les fiches utiles à cette personne et rédigent l'analyse à afficher.
#    Seules des fiches du catalogue peuvent être choisies : les numéros sont vérifiés ici, tout numéro inconnu est écarté.
#
# Le modèle est appelé avec la clé ANTHROPIC_API_KEY, rangée dans un secret Modal : elle n'est jamais écrite dans le code.
import base64, io, json, re

MODELE = "claude-sonnet-5-5"
ZONES = ["forehead", "temples", "brows", "eyes", "nose", "cheeks", "mouth", "chin", "jaw"]
NOMS_ZONES = {"forehead": "front (et cheveux)", "temples": "tempes", "brows": "sourcils", "eyes": "yeux", "nose": "nez",
              "cheeks": "joues (peau)", "mouth": "bouche", "chin": "menton (barbe)", "jaw": "mâchoire (rasage)"}

CONSIGNE_ANALYSTE = """Tu es l'analyste visuel d'AVIRSO, une application de visagisme (coiffure, barbe, soin, maquillage, lunettes).
On te donne trois photos d'une même personne : face, puis chaque côté. Décris son apparence pour qu'un visagiste puisse la conseiller.

Règles :
- Décris seulement ce qui se voit. Si un point ne se voit pas bien (lumière, flou, cadrage), écris « indéterminé ».
- Aucune note de beauté, aucun défaut, aucun jugement. Les caractéristiques sont décrites, jamais corrigées.
- Ne devine ni l'origine, ni l'âge, ni le genre, ni une maladie ou un problème de peau médical.
- La carnation et le sous-ton servent au choix des teintes de maquillage : décris-les avec les mots d'un maquilleur.
- La teinte Monk et la couleur des yeux sont des estimations sur photo : la lumière les fausse, dis-le dans « limites » si l'éclairage est coloré ou faible.
- Réponds uniquement par un objet JSON valide, sans texte autour, de cette forme :
{
 "cheveux": {"texture": "raides|ondulés|bouclés|crépus|indéterminé", "type_boucle": "1A à 4C, ou indéterminé", "longueur": "très courts|courts|mi-longs|longs|indéterminé", "coupe": "description courte", "couleur": "description courte", "remarques": "description courte"},
 "barbe": {"presence": "aucune|naissante|courte|moyenne|longue|indéterminé", "description": "forme, densité, contours", "poils_blancs": "oui|non|indéterminé"},
 "peau": {"carnation": "très claire|claire|moyenne|mate|foncée|très foncée|indéterminé", "teinte_monk": "nombre de 1 (la plus claire) à 10 (la plus foncée) sur l'échelle Monk, estimé sur les photos, ou indéterminé", "sous_ton": "chaud|froid|neutre|olive|indéterminé", "taches_de_rousseur": "aucune|quelques-unes|nombreuses|indéterminé", "rougeurs": "aucune|légères|marquées|indéterminé (la lumière et la chaleur peuvent en créer)", "aspect_visible": "brillance, sécheresse ou taches visibles sur les photos, ou indéterminé"},
 "yeux": {"couleur": "marron foncé|marron|noisette|vert|gris|bleu|indéterminé", "cils": "courts|moyens|longs, droits ou recourbés, ou indéterminé", "forme": "en amande|ronds|tombants|paupière tombante|sans pli (monolid)|enfoncés|indéterminé"},
 "sourcils": "forme et densité",
 "visage": {"forme": "ovale|rond|carré|long|cœur|losange|triangle|indéterminé", "traits_marquants": ["2 à 4 traits décrits positivement"]},
 "lunettes": "portées|non portées",
 "fiabilite": "bonne|moyenne|faible",
 "limites": ["ce qui n'a pas pu être vu correctement"]
}"""

CONSIGNE_CONSEILLER = """Tu es le visagiste d'AVIRSO. Tu reçois la description d'une personne faite par l'analyste visuel, ses éventuelles réponses,
et le catalogue des fiches sourcées de la bibliothèque AVIRSO (numéro, sujet, titre, texte, niveau de la source, nature de la fiche, mois de relevé).
La nature dit ce que vaut chaque fiche : « Établi » (autorité de santé ou large consensus), « Études publiées », « Avis médical »,
« Repère » (échelle conventionnelle), « Savoir-faire » (pratique de professionnels ou de marques, non testée), « Hypothèse » (science débattue),
« Tendance · mois année » (mode du moment, pas une preuve).

Ta tâche :
1. Choisir dans le catalogue de 8 à 20 fiches vraiment utiles à cette personne (par exemple : fiches cheveux crépus et coiffures protectrices
   pour des cheveux crépus, rasage et poils incarnés pour une barbe courte et frisée, peaux foncées pour une carnation foncée,
   taches de rousseur si elles sont visibles, faux cils selon la forme de l'œil, couleurs des vêtements selon les yeux).
   N'utilise que des numéros présents dans le catalogue. Pour chacune, écris en une phrase (25 mots au plus) pourquoi elle la concerne,
   en t'appuyant sur la description, sans affirmer ce que la description ne dit pas.
2. Rédiger l'analyse affichée à l'arrivée : 110 à 170 mots, en français, au vouvoiement, chaleureuse et précise, comme un visagiste qui parle.
   Décris d'abord le visage, les cheveux, la barbe et la peau, en valorisant sans flatter ni juger ; puis dis en une phrase ce qui peut
   le mettre en valeur ; termine par une invitation à toucher les zones du visage pour aller plus loin. Si la fiabilité est faible, dis-le simplement.
3. Donner 3 à 5 points à retenir (titre de 2 à 5 mots, texte de 25 mots au plus), chacun rattaché à une zone parmi :
   forehead (front et cheveux), temples, brows, eyes, nose, cheeks (peau), mouth, chin (barbe), jaw (rasage).

Règles : aucune note de beauté, aucun défaut, aucun diagnostic médical, aucune marque de produit, rien sur l'origine ou l'âge.
Les conseils viennent des fiches choisies : n'en invente pas d'autres.
Ne présente jamais un savoir-faire, une hypothèse ou une tendance comme un fait prouvé : dis « d'après les coiffeurs », « c'est une hypothèse »,
« c'est tendance en <mois année> ». Une tendance n'est jamais une recommandation de santé.
Réponds uniquement par un objet JSON valide, sans texte autour :
{"texte": "...", "points": [{"titre": "...", "texte": "...", "zone": "..."}], "selection": [{"id": 0, "pourquoi": "..."}]}"""


def _image(contenu: bytes) -> dict:
    """Photo réduite à 1280 px de côté, en JPEG, pour l'envoi au modèle."""
    from PIL import Image, ImageOps
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except Exception:
        pass
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(contenu))).convert("RGB")
    im.thumbnail((1280, 1280))
    b = io.BytesIO(); im.save(b, "JPEG", quality=88)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(b.getvalue()).decode()}}


def _json(texte: str) -> dict:
    m = re.search(r"\{.*\}", texte, re.S)
    if not m:
        raise ValueError("réponse sans JSON")
    return json.loads(m.group(0))


def _obj(props: dict) -> dict:
    """Objet JSON strict (toutes les clés requises, aucune clé en plus), comme l'exigent les sorties structurées."""
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


S = {"type": "string"}
SCHEMA_ANALYSTE = _obj({
    "cheveux": _obj({"texture": S, "type_boucle": S, "longueur": S, "coupe": S, "couleur": S, "remarques": S}),
    "barbe": _obj({"presence": S, "description": S, "poils_blancs": S}),
    "peau": _obj({"carnation": S, "teinte_monk": S, "sous_ton": S, "taches_de_rousseur": S, "rougeurs": S, "aspect_visible": S}),
    "yeux": _obj({"couleur": S, "cils": S, "forme": S}),
    "sourcils": S,
    "visage": _obj({"forme": S, "traits_marquants": {"type": "array", "items": S}}),
    "lunettes": S, "fiabilite": S, "limites": {"type": "array", "items": S}})
SCHEMA_CONSEILLER = _obj({
    "texte": S,
    "points": {"type": "array", "items": _obj({"titre": S, "texte": S, "zone": {"type": "string", "enum": ZONES}})},
    "selection": {"type": "array", "items": _obj({"id": {"type": "integer"}, "pourquoi": S})}})


def _appeler(client, systeme: str, contenu: list, max_tokens: int, schema: dict | None = None) -> dict:
    """Appel du modèle. Avec un schéma, l'API contraint la réponse à un JSON valide conforme (sorties structurées),
    ce qui évite les JSON mal formés (guillemets non échappés dans un texte en français). Une seconde tentative si besoin."""
    derniere = None
    for _ in range(2):
        # sorties structurées : la réponse texte est un JSON conforme au schéma (passé dans le corps brut, compatible avec tout SDK récent)
        extra = {"extra_body": {"output_config": {"format": {"type": "json_schema", "schema": schema}}}} if schema else {}
        r = client.messages.create(model=MODELE, max_tokens=max_tokens, system=systeme, messages=[{"role": "user", "content": contenu}], **extra)
        if getattr(r, "stop_reason", "") == "max_tokens":
            derniere = ValueError("réponse coupée (longueur maximale atteinte)"); max_tokens = int(max_tokens * 1.5); continue
        types = [getattr(b, "type", "?") for b in r.content]
        try:
            return _json("".join(b.text for b in r.content if getattr(b, "type", "") == "text"))
        except Exception as e:
            derniere = f"{e} ; blocs reçus {types}, arrêt {getattr(r, 'stop_reason', '?')}, schéma {'oui' if schema else 'non'}"
    raise ValueError(f"réponse illisible du modèle ({derniere})")


def nettoyer(conseil: dict, catalogue: list) -> dict:
    """Ne garde que des fiches du catalogue, des zones connues et des textes de longueur raisonnable."""
    ids = {f["id"] for f in catalogue}
    vus, selection = set(), []
    for s in conseil.get("selection") or []:
        try:
            i = int(s.get("id"))
        except Exception:
            continue
        if i in ids and i not in vus:
            vus.add(i); selection.append({"id": i, "pourquoi": str(s.get("pourquoi", ""))[:220]})
    points = [{"titre": str(p.get("titre", ""))[:60], "texte": str(p.get("texte", ""))[:240], "zone": p.get("zone") if p.get("zone") in ZONES else "cheeks"}
              for p in (conseil.get("points") or [])[:5] if p.get("titre")]
    texte = str(conseil.get("texte", "")).strip()[:1600]
    if not texte:
        raise ValueError("analyse vide")
    return {"texte": texte, "points": points, "selection": selection[:24]}


def analyser(client, photos: list, catalogue: list, reponses: dict | None = None) -> dict:
    """photos : contenu des fichiers (face, puis les côtés). Renvoie la description, l'analyse à afficher, les points et les fiches choisies."""
    vues = [_image(p) for p in photos[:3]]
    description = _appeler(client, CONSIGNE_ANALYSTE, vues + [{"type": "text", "text": "Voici les photos (face, puis les deux côtés). Décris l'apparence selon la forme demandée."}], 2000, SCHEMA_ANALYSTE)
    cat = [{"id": f["id"], "sujet": f["sujet"], "titre": f["titre"], "texte": f["texte"][:400], "niveau": f["niveau"], "nature": f.get("nature", ""), "releve": f.get("releve", "")} for f in catalogue]
    demande = json.dumps({"description": description, "reponses": reponses or {}, "catalogue": cat}, ensure_ascii=False)
    conseil = nettoyer(_appeler(client, CONSIGNE_CONSEILLER, [{"type": "text", "text": demande}], 4000, SCHEMA_CONSEILLER), catalogue)
    return {"ok": True, "description": description, **conseil, "fiabilite": description.get("fiabilite", "indéterminé"),
            "limites": description.get("limites", []), "modele": MODELE}
