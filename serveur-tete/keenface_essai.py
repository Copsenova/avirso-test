# Essai KeenFace (une fois, à la main) : envoie 3 à 7 photos, récupère la tête (OBJ + texture) dans un dossier PRIVÉ.
#   python3 -m modal run serveur-tete/keenface_essai.py --dossier ~/Desktop/avirso-photos-privees --sortie ~/Desktop/avirso-photos-privees/tete_keenface.zip
# Les photos ne passent jamais par le dépôt public ; la clé vient du secret Modal « keentools » (variable KEENTOOLS_API_KEY).
import os
import modal

app = modal.App("avirso-keenface-essai")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests==2.32.3").add_local_file("serveur-tete/keenface.py", "/root/keenface.py")


@app.function(image=image, secrets=[modal.Secret.from_name("keentools")], timeout=900)
def reconstruire_distant(photos: list[bytes]) -> dict:
    import requests, keenface
    r = keenface.reconstruire(photos, requests.Session())
    return {"id": r["id"], "zip": r["zip"], "secondes": r["secondes"]}


@app.local_entrypoint()
def main(dossier: str, sortie: str):
    dossier, sortie = os.path.expanduser(dossier), os.path.expanduser(sortie)
    noms = sorted(f for f in os.listdir(dossier) if f.lower().endswith((".jpg", ".jpeg")))[:7]
    print("photos :", noms)
    r = reconstruire_distant.remote([open(os.path.join(dossier, f), "rb").read() for f in noms])
    open(sortie, "wb").write(r["zip"])
    print(f"tête reçue en {r['secondes']} s : {sortie} ({len(r['zip']) // 1024} Ko)")
