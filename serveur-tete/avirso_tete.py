# AVIRSO — serveur « tête qui tourne » (Modal).
#
# Reçoit quelques photos d'une même personne (face, trois-quarts), fabrique la suite d'images de la tête
# qui tourne (script tete.py, validé sur Colab), et renvoie ces images. Rien n'est gardé :
# les photos et les images vivent dans un dossier temporaire, effacé à la fin du calcul.
#
# Mise en ligne :   modal deploy serveur-tete/avirso_tete.py
# Essai sans site : modal run serveur-tete/avirso_tete.py --photos "a.jpg,b.jpg,c.jpg"
#
# Aucune clé n'est écrite ici : l'accès à Modal se fait par « modal token new » sur la machine qui déploie.
import os
import modal

LP_COMMIT = "main"      # à figer sur un commit précis avant l'ouverture au public
POIDS = "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait"
FICHIERS = [
    "base_models/appearance_feature_extractor.pth",
    "base_models/motion_extractor.pth",
    "base_models/spade_generator.pth",
    "base_models/warping_module.pth",
    "retargeting_models/stitching_retargeting_module.pth",
]
DECOUPE = "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite"
ORIGINES = ["https://copsenova.github.io", "http://127.0.0.1:5173", "http://localhost:5173"]
MAX_PHOTOS, MAX_OCTETS = 5, 12 * 1024 * 1024

# Les agents (analyse par modèle de vision) ne s'activent que si la clé est rangée dans le secret Modal « anthropic »
# (variable ANTHROPIC_API_KEY) et que l'on déploie avec AVEC_ANALYSE=1. Sans cela, /analyses répond « pas encore activée ».
AVEC_ANALYSE = os.environ.get("AVEC_ANALYSE") == "1"
# Nom du secret Modal : « anthropic » par défaut ; SECRET_ANTHROPIC=<nom> au déploiement si le secret porte un autre nom.
NOM_SECRET = os.environ.get("SECRET_ANTHROPIC", "anthropic")
SECRETS = [modal.Secret.from_name(NOM_SECRET, required_keys=["ANTHROPIC_API_KEY"])] if AVEC_ANALYSE else []
# Ces deux réglages sont relus dans le conteneur : on les inscrit dans l’image, sinon le serveur en marche les croirait absents.

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "wget", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.5.1", "torchvision==0.20.1", "numpy<2", "opencv-python-headless==4.10.0.84", "pyyaml", "pillow",
        "pillow-heif", "imageio[ffmpeg]", "scipy", "tqdm", "rich", "ai-edge-litert", "fastapi[standard]",
        "python-multipart", "anthropic",
    )
    .run_commands(
        "git clone https://github.com/KwaiVGI/LivePortrait /LivePortrait",
        f"cd /LivePortrait && git checkout {LP_COMMIT} && mkdir -p pw",
        *[f"wget -q -P /LivePortrait/pw {POIDS}/{f}" for f in FICHIERS],
        f"wget -q -P /LivePortrait/pw {DECOUPE}",
    )
    .env({"AVEC_ANALYSE": "1" if AVEC_ANALYSE else "0", "SECRET_ANTHROPIC": NOM_SECRET, "VERSION_SITE": "2026-11-25-reveil-coupes"})
    .add_local_file("essai-generation/tete.py", "/LivePortrait/tete.py")
    .add_local_file("essai-generation/mise_en_scene.py", "/LivePortrait/mise_en_scene.py")
    .add_local_file("essai-generation/couleur.py", "/LivePortrait/couleur.py")
    .add_local_file("serveur-tete/agents.py", "/root/agents.py")
    .add_local_file("serveur-tete/savoir.json", "/root/savoir.json")
    .add_local_file("serveur-tete/coupes.py", "/root/coupes.py")
    .add_local_file("serveur-tete/catalogue.json", "/root/catalogue.json")
)

app = modal.App("avirso-tete", image=image)

# ---------------------------------------------------------------- essai de coupe par édition d'image (Qwen-Image-Edit-2511, Apache 2.0)
# Les poids (plusieurs dizaines de Go) sont gardés dans un volume Modal, téléchargés une seule fois. Rien d'autre n'est gardé.
MODELE_COUPE = "Qwen/Qwen-Image-Edit-2511"
LORA_RAPIDE, FICHIER_RAPIDE = "lightx2v/Qwen-Image-Edit-2511-Lightning", "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
poids = modal.Volume.from_name("avirso-poids", create_if_missing=True)
image_coupe = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("torch==2.6.0", "torchvision==0.21.0", "transformers>=4.51", "accelerate", "peft>=0.17", "safetensors", "sentencepiece",
                 "huggingface_hub[hf_transfer]", "pillow", "pillow-heif", "git+https://github.com/huggingface/diffusers")
    .env({"HF_HOME": "/poids", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .add_local_file("serveur-tete/coupes.py", "/root/coupes.py")
    .add_local_file("serveur-tete/catalogue.json", "/root/catalogue.json")
)


@app.function(image=image_coupe, volumes={"/poids": poids}, timeout=3600, cpu=4.0)
def precharger_coupe() -> str:
    """Télécharge les poids du modèle de coupe dans le volume (une seule fois)."""
    from huggingface_hub import snapshot_download
    chemin = snapshot_download(MODELE_COUPE)
    snapshot_download(LORA_RAPIDE, allow_patterns=[FICHIER_RAPIDE])
    poids.commit()
    return chemin


@app.cls(image=image_coupe, gpu="H100", volumes={"/poids": poids}, timeout=900, scaledown_window=120, max_containers=1)
class Retoucheur:
    @modal.enter()
    def charger(self):
        import torch
        from diffusers import QwenImageEditPlusPipeline
        self.pipe = QwenImageEditPlusPipeline.from_pretrained(MODELE_COUPE, torch_dtype=torch.bfloat16).to("cuda")
        self.pipe.set_progress_bar_config(disable=True)
        # version accélérée (Lightning, Apache 2.0) : 4 à 8 pas au lieu de 40, sans guidage
        self.rapide = os.environ.get("COUPE_RAPIDE", "1") == "1"
        if self.rapide:
            self.pipe.load_lora_weights(LORA_RAPIDE, weight_name=FICHIER_RAPIDE)

    def _editer(self, images, texte: str):
        import torch
        pas = int(os.environ.get("PAS_COUPE", "8" if self.rapide else "40"))
        sortie = self.pipe(image=images, prompt=texte, negative_prompt=" ", true_cfg_scale=1.0 if self.rapide else 4.0, guidance_scale=1.0,
                           num_inference_steps=pas, generator=torch.manual_seed(0))
        return sortie.images[0]

    @modal.method()
    def retoucher(self, photos: list[bytes], coupe: str | None = None, couleur: str | None = None, barbe: str | None = None,
                  texture_barbe: str | None = None, couleur_barbe: str | None = None) -> dict:
        """photos : [face, trois-quarts...]. Renvoie la face retouchée puis les autres vues (WebP base64)."""
        import base64, io, sys, time
        from PIL import Image, ImageOps
        sys.path.insert(0, "/root")
        from coupes import consigne
        if not photos:
            return {"ok": True, "reveil": True}
        t0 = time.time()
        try:
            def ouvrir(b):
                try:
                    from pillow_heif import register_heif_opener
                    register_heif_opener()
                except Exception:
                    pass
                im = ImageOps.exif_transpose(Image.open(io.BytesIO(b))).convert("RGB")
                im.thumbnail((1024, 1024))
                return im
            def webp(im):
                f = io.BytesIO(); im.save(f, "WEBP", quality=92); return base64.b64encode(f.getvalue()).decode()
            ims = [ouvrir(b) for b in photos[:3]]
            face = self._editer([ims[0]], consigne(coupe, couleur, "face", barbe, texture_barbe, couleur_barbe))
            t_face = time.time() - t0
            # chaque trois-quarts est retouché seul (avec la face en référence, le modèle remettait la tête de face)
            vues = [self._editer([im], consigne(coupe, couleur, "trois_quarts", barbe, texture_barbe, couleur_barbe)) for im in ims[1:]]
            return {"ok": True, "face": webp(face), "vues": [webp(v) for v in vues], "secondes": round(time.time() - t0, 1), "secondes_face": round(t_face, 1)}
        except ValueError as e:
            return {"ok": False, "erreur": str(e)}
        except Exception as e:
            return {"ok": False, "erreur": "la retouche a échoué", "detail": f"{type(e).__name__}: {str(e)[:300]}"}


@app.function(gpu="T4", cpu=8.0, memory=8192, timeout=900, max_containers=1, scaledown_window=150)
def fabriquer(photos: list[bytes], cote: int = 960) -> dict:
    """Fabrique la suite d'images. `photos` : contenu des fichiers. Renvoie les images (WebP) et leurs angles."""
    import base64, glob, os, re, shutil, subprocess, tempfile, time
    import cv2
    if not photos:      # simple réveil : la machine démarre pendant que la personne prend ses photos
        return {"ok": True, "reveil": True}
    t0 = time.time()
    dossier = tempfile.mkdtemp(prefix="avirso_")
    try:
        chemins = []
        for n, contenu in enumerate(photos):
            ch = os.path.join(dossier, f"photo{n}")
            with open(ch, "wb") as f:
                f.write(contenu)
            chemins.append(ch)
        r = subprocess.run(
            ["python", "tete.py", os.path.join(dossier, "t"), *chemins],
            cwd="/LivePortrait", capture_output=True, text=True, env={**os.environ, "TAILLE": "1024", "COTE": str(cote), "LEGER": "1", "FILS": "8", "DEMI": "1"},
        )
        journal = [l for l in r.stdout.splitlines() if l.strip()]
        if r.returncode != 0:
            return {"ok": False, "erreur": "le calcul a échoué", "detail": (r.stderr or "")[-800:], "journal": journal[-12:]}
        fichiers = sorted(glob.glob(os.path.join(dossier, "t_[0-9]*.webp"))) or sorted(glob.glob(os.path.join(dossier, "t_[0-9]*.jpg")))
        bornes = None
        for l in journal:
            m = re.search(r"de ([+-][\d.]+)° à ([+-][\d.]+)°", l)
            if m and "images de" in l:
                bornes = (float(m.group(1)), float(m.group(2)))
        if not fichiers or bornes is None:
            return {"ok": False, "erreur": "aucune image produite", "journal": journal[-12:]}
        images = []
        for f in fichiers:
            images.append(base64.b64encode(open(f, "rb").read()).decode())      # déjà à la bonne taille, transparence gardée
        n = len(images)
        angles = [bornes[0] + (bornes[1] - bornes[0]) * k / max(n - 1, 1) for k in range(n)]
        return {"ok": True, "angles": angles, "images": images, "cote": cote, "transparent": bool(images) and fichiers[0].endswith(".webp"), "secondes": round(time.time() - t0, 1),
                "journal": [l for l in journal if "photo" in l or "inclinaison" in l or "hochement" in l][-8:],
                "temps": [l for l in journal if l.startswith("temps") or "s par image" in l]}
    finally:
        shutil.rmtree(dossier, ignore_errors=True)      # rien n'est gardé


@app.function(timeout=300, max_containers=4, secrets=SECRETS)
def analyser_photos(photos: list[bytes], reponses: dict | None = None) -> dict:
    """Analyste, chercheur et conseiller : description de l'apparence, choix des fiches sourcées, analyse à afficher. Rien n'est gardé."""
    import json, sys, time
    sys.path.insert(0, "/root")
    t0 = time.time()
    try:
        import anthropic, agents
        r = agents.analyser(anthropic.Anthropic(), photos, json.load(open("/root/savoir.json", encoding="utf-8")), reponses)
        r["secondes"] = round(time.time() - t0, 1)
        return r
    except Exception as e:
        return {"ok": False, "erreur": "l'analyse a échoué", "detail": f"{type(e).__name__}: {str(e)[:300]}"}


@app.function(max_containers=2)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def site():
    from fastapi import FastAPI, File, Form, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware

    web = FastAPI(title="AVIRSO tête", docs_url=None, redoc_url=None)
    web.add_middleware(CORSMiddleware, allow_origins=ORIGINES, allow_methods=["GET", "POST"], allow_headers=["*"])

    @web.get("/")
    def accueil():
        return {"service": "avirso-tete", "etat": "en marche", "analyse": AVEC_ANALYSE}

    @web.post("/reveil")
    async def reveil():
        await fabriquer.spawn.aio([])      # aucune donnée envoyée : sert seulement à démarrer la machine de calcul
        return {"ok": True}

    @web.post("/reveil-coupes")
    async def reveil_coupes():
        await Retoucheur().retoucher.spawn.aio([], None)      # le modèle de coupe (GPU coûteux) ne démarre que si la personne ouvre l'essai de style
        return {"ok": True}

    @web.post("/taches")
    async def creer(photos: list[UploadFile] = File(...)):
        if not 1 <= len(photos) <= MAX_PHOTOS:
            raise HTTPException(400, f"envoyez de 1 à {MAX_PHOTOS} photos")
        contenus = []
        for p in photos:
            c = await p.read()
            if len(c) > MAX_OCTETS:
                raise HTTPException(413, "photo trop lourde (12 Mo au plus)")
            if not (c[:3] == b"\xff\xd8\xff" or c[:8] == b"\x89PNG\r\n\x1a\n" or c[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1", b"ftypheif") or c[:4] == b"RIFF"):
                raise HTTPException(415, "format de photo non reconnu (JPEG, PNG, HEIC ou WebP)")
            contenus.append(c)
        appel = await fabriquer.spawn.aio(contenus)
        return {"id": appel.object_id}

    @web.post("/analyses")
    async def creer_analyse(photos: list[UploadFile] = File(...), reponses: str = Form("{}")):
        import json
        if not AVEC_ANALYSE:
            raise HTTPException(503, "analyse pas encore activée")
        if not 1 <= len(photos) <= MAX_PHOTOS:
            raise HTTPException(400, f"envoyez de 1 à {MAX_PHOTOS} photos")
        contenus = []
        for p in photos:
            c = await p.read()
            if len(c) > MAX_OCTETS:
                raise HTTPException(413, "photo trop lourde (12 Mo au plus)")
            contenus.append(c)
        try:
            rep = json.loads(reponses) if reponses else {}
        except Exception:
            rep = {}
        # seules deux clés passent : les objectifs choisis dans une liste fermée, et un message court de la personne
        rep = rep if isinstance(rep, dict) else {}
        permis = {"valeur", "coupe", "barbe", "peau", "maquillage", "lunettes", "decouvrir"}
        rep = {"objectifs": [o for o in rep.get("objectifs", []) if isinstance(o, str) and o in permis][:7],
               "message": rep.get("message", "")[:300] if isinstance(rep.get("message"), str) else ""}
        appel = await analyser_photos.spawn.aio(contenus, rep)
        return {"id": appel.object_id}

    @web.post("/coupes")
    async def creer_coupe(photos: list[UploadFile] = File(...), coupe: str = Form(""), couleur: str = Form(""), barbe: str = Form(""),
                          texture_barbe: str = Form(""), couleur_barbe: str = Form("")):
        import sys
        sys.path.insert(0, "/root")
        from coupes import valider_demande, BARBES, TEXTURES_BARBE, COULEURS_BARBE
        try:
            coupe, teinte = valider_demande(coupe, couleur)
        except ValueError:
            raise HTTPException(400, "coupe inconnue")
        barbe = barbe if barbe in BARBES else None
        texture_barbe = texture_barbe if texture_barbe in TEXTURES_BARBE else None
        couleur_barbe = couleur_barbe if couleur_barbe in COULEURS_BARBE else None
        if not (coupe or teinte or barbe or texture_barbe or couleur_barbe):
            raise HTTPException(400, "rien à changer")
        if not 1 <= len(photos) <= 3:
            raise HTTPException(400, "envoyez de 1 à 3 photos (la face d'abord)")
        contenus = []
        for p in photos:
            c = await p.read()
            if len(c) > MAX_OCTETS:
                raise HTTPException(413, "photo trop lourde (12 Mo au plus)")
            contenus.append(c)
        appel = await Retoucheur().retoucher.spawn.aio(contenus, coupe, teinte, barbe, texture_barbe, couleur_barbe)
        return {"id": appel.object_id}

    @web.get("/coupes/{ident}")
    async def lire_coupe(ident: str):
        return await lire(ident)

    @web.get("/analyses/{ident}")
    async def lire_analyse(ident: str):
        return await lire(ident)

    @web.get("/taches/{ident}")
    async def lire(ident: str):
        from fastapi.responses import JSONResponse
        try:
            appel = modal.FunctionCall.from_id(ident)
            return await appel.get.aio(timeout=0)
        except TimeoutError:
            return JSONResponse({"etat": "en cours"}, status_code=202)
        except Exception:
            raise HTTPException(404, "tâche inconnue ou expirée")

    return web


@app.local_entrypoint()
def essai(photos: str, sortie: str = "essai_tete"):
    """Essai direct, sans le site : modal run serveur-tete/avirso_tete.py --photos "a.jpg,b.jpg,c.jpg" """
    import base64, os
    r = fabriquer.remote([open(p, "rb").read() for p in photos.split(",")])
    print({k: v for k, v in r.items() if k != "images"})
    if r.get("ok"):
        os.makedirs(sortie, exist_ok=True)
        for n, im in enumerate(r["images"]):
            open(os.path.join(sortie, f"{n:03d}.webp"), "wb").write(base64.b64decode(im))
        print(len(r["images"]), "images écrites dans", sortie)


essais = modal.Volume.from_name("avirso-essais", create_if_missing=True)


@app.function(image=image_coupe, volumes={"/essais": essais}, timeout=7200)
def essai_coupes_distant(contenus: list[bytes], demandes: list[dict], dossier: str) -> None:
    """Essai mené entièrement sur Modal (le poste peut se déconnecter). Résultats dans le volume avirso-essais, à effacer après lecture."""
    import base64, json, os, time
    os.makedirs(f"/essais/{dossier}", exist_ok=True); journal = []
    def noter(l):
        journal.append(l); open(f"/essais/{dossier}/journal.txt", "w").write("\n".join(journal)); essais.commit()
    noter(f"poids : {precharger_coupe.remote()}")
    r = Retoucheur()
    for d in demandes:
        t0 = time.time(); res = r.retoucher.remote(contenus, **d); nom = "_".join(str(v) for v in d.values() if v) or "rien"
        if not res.get("ok"):
            noter(f"{nom} ÉCHEC {json.dumps(res)[:400]}"); continue
        for k, b in enumerate([res["face"], *res["vues"]]):
            open(f"/essais/{dossier}/{nom}_{k}.webp", "wb").write(base64.b64decode(b))
        noter(f"{nom} face {res['secondes_face']} s ; total {res['secondes']} s ; aller-retour {round(time.time() - t0, 1)} s")
    noter("FIN")


@app.local_entrypoint()
def essai_coupes(photos: str, demandes: str = '[{"coupe": "degrade"}]', dossier: str = "essai"):
    """modal run --detach serveur-tete/avirso_tete.py::essai_coupes --photos "face.jpg,g.jpg,d.jpg" --demandes '[{"coupe": "afro", "couleur": "noir"}]'
    puis : modal volume get avirso-essais <dossier> ; modal volume rm -r avirso-essais <dossier>"""
    contenus = [open(p, "rb").read() for p in photos.split(",")]
    import json
    appel = essai_coupes_distant.spawn(contenus, json.loads(demandes), dossier)
    print("essai lancé :", appel.object_id)
