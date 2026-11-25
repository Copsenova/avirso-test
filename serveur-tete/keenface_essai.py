# Essai KeenFace (une fois, à la main) : envoie 3 à 7 photos, récupère la tête (OBJ + texture) dans un dossier PRIVÉ.
#   python3 -m modal run serveur-tete/keenface_essai.py --dossier ~/Desktop/avirso-photos-privees --sortie ~/Desktop/avirso-photos-privees/tete_keenface.zip
# Les photos ne passent jamais par le dépôt public ; la clé vient du secret Modal « keentools » (variable KEENTOOLS_API_KEY).
import os
import modal

app = modal.App("avirso-keenface-essai")
essais = modal.Volume.from_name("avirso-essais", create_if_missing=True)
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests==2.32.3").add_local_file("serveur-tete/keenface.py", "/root/keenface.py")


@app.function(image=image, secrets=[modal.Secret.from_name("keentools")], volumes={"/essais": essais}, timeout=900)
def reconstruire_distant(photos: list[bytes]) -> dict:
    import json, requests, keenface
    try:
        r = keenface.reconstruire(photos, requests.Session())
    except Exception as e:      # le resultat (ou l'erreur) reste lisible dans le volume, meme si le lanceur local s'est arrete
        open("/essais/keenface_resultat.json", "w").write(json.dumps({"ok": False, "erreur": str(e)})); essais.commit(); raise
    open("/essais/keenface_tete.zip", "wb").write(r["zip"])
    open("/essais/keenface_resultat.json", "w").write(json.dumps({"ok": True, "id": r["id"], "secondes": r["secondes"], "octets": len(r["zip"])}))
    essais.commit()
    return {"id": r["id"], "zip": r["zip"], "secondes": r["secondes"]}


@app.local_entrypoint()
def main(dossier: str, sortie: str):
    dossier, sortie = os.path.expanduser(dossier), os.path.expanduser(sortie)
    noms = sorted(f for f in os.listdir(dossier) if f.lower().endswith((".jpg", ".jpeg")))[:7]
    print("photos :", noms)
    r = reconstruire_distant.remote([open(os.path.join(dossier, f), "rb").read() for f in noms])
    open(sortie, "wb").write(r["zip"])
    print(f"tête reçue en {r['secondes']} s : {sortie} ({len(r['zip']) // 1024} Ko)")
