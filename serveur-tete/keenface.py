# Tête 3D ressemblante à partir de 3 à 7 photos : service KeenFace (KeenTools), API REST.
# Déroulé documenté par KeenTools : init (id + adresses de dépôt) → PUT des photos → process → get-status (gratuit) → get-3d-model (OBJ + texture, ZIP).
# Le téléchargement est facturé à CHAQUE appel : on télécharge une seule fois et on garde le résultat.
# La clé vient du secret Modal (variable KEENTOOLS_API_KEY) ; elle n'apparaît jamais dans le code ni dans les journaux.
import os, time

API = os.environ.get("KEENFACE_API", "https://api.keenface.ai")
FORMAT = {"mesh_format": "obj", "texture": "jpg"}


class ErreurKeen(RuntimeError):
    pass


def _cle() -> str:
    k = os.environ.get("KEENTOOLS_API_KEY", "").strip()
    if not k:
        raise ErreurKeen("clé KeenTools absente : ajoutez KEENTOOLS_API_KEY dans les secrets Modal")
    return k


def _trouver_id(j: dict) -> str:
    """L'identifiant de la séance, quel que soit le nom exact du champ (avatar_id, id, avatar.id…)."""
    for k in ("avatar_id", "id", "avatarId"):
        if isinstance(j.get(k), (str, int)):
            return str(j[k])
    for v in j.values():
        if isinstance(v, dict):
            try:
                return _trouver_id(v)
            except ErreurKeen:
                pass
    raise ErreurKeen(f"identifiant introuvable dans la réponse (champs : {sorted(j)})")


def _trouver_adresses(j, n: int) -> list[str]:
    """Les adresses de dépôt des photos (liste d'URL, éventuellement d'objets {url: …})."""
    trouve: list[str] = []
    def parcourir(x):
        if isinstance(x, str) and x.startswith("http"):
            trouve.append(x)
        elif isinstance(x, dict):
            for k in ("upload_url", "url", "put_url"):
                if isinstance(x.get(k), str) and x[k].startswith("http"):
                    trouve.append(x[k]); return
            for v in x.values():
                parcourir(v)
        elif isinstance(x, list):
            for v in x:
                parcourir(v)
    parcourir({k: v for k, v in j.items() if "upload" in k.lower() or "url" in k.lower()} if isinstance(j, dict) else j)
    if len(trouve) < n:
        raise ErreurKeen(f"{len(trouve)} adresse(s) de dépôt pour {n} photos (champs : {sorted(j) if isinstance(j, dict) else type(j)})")
    return trouve[:n]


def reconstruire(photos: list[bytes], session, attente_max: float = 420, pas: float = 6, dormir=time.sleep) -> dict:
    """photos : 3 à 7 JPEG (face d'abord). session : objet type requests.Session. Renvoie {id, zip (octets), secondes}."""
    if not 3 <= len(photos) <= 7:
        raise ErreurKeen("il faut de 3 à 7 photos")
    t0 = time.time(); h = {"Authorization": f"Bearer {_cle()}"}
    r = session.post(f"{API}/v1/avatar/init", headers={**h, "Content-Type": "application/json"}, json={"image_count": len(photos)}, timeout=60)
    if r.status_code >= 400:
        raise ErreurKeen(f"init refusé ({r.status_code}) : {r.text[:300]}")
    j = r.json(); ident = _trouver_id(j)
    for adr, p in zip(_trouver_adresses(j, len(photos)), photos):
        rr = session.put(adr, headers={"Content-Type": "image/jpeg"}, data=p, timeout=120)
        if rr.status_code >= 400:
            raise ErreurKeen(f"dépôt d'une photo refusé ({rr.status_code})")
    r = session.post(f"{API}/v1/avatar/{ident}/process", headers={**h, "Content-Type": "application/json"},
                     json={"focal_length_type": {"focal_length_type": "estimate_common"}}, timeout=60)
    if r.status_code >= 400:
        raise ErreurKeen(f"reconstruction refusée ({r.status_code}) : {r.text[:300]}")
    debut = time.time()
    while True:
        s = session.get(f"{API}/v1/avatar/{ident}/get-status", headers=h, timeout=30)
        etat = str((s.json() if s.status_code < 400 else {}).get("status", "")).lower()
        if etat == "completed":
            break
        if etat in ("failed", "error", "cancelled"):
            raise ErreurKeen(f"reconstruction échouée : {s.text[:300]}")
        if time.time() - debut > attente_max:
            raise ErreurKeen("reconstruction trop longue (plus de 7 minutes)")
        dormir(pas)
    z = session.get(f"{API}/v1/avatar/{ident}/get-3d-model", headers=h, params=FORMAT, timeout=180, allow_redirects=True)      # FACTURÉ : un seul appel
    if z.status_code >= 400 or not z.content.startswith(b"PK"):
        raise ErreurKeen(f"téléchargement du modèle refusé ({z.status_code})")
    return {"id": ident, "zip": z.content, "secondes": round(time.time() - t0, 1)}
