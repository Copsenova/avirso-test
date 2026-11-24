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

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "wget", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.5.1", "torchvision==0.20.1", "numpy<2", "opencv-python-headless==4.10.0.84", "pyyaml", "pillow",
        "pillow-heif", "imageio[ffmpeg]", "scipy", "tqdm", "rich", "ai-edge-litert", "fastapi[standard]",
        "python-multipart",
    )
    .run_commands(
        "git clone https://github.com/KwaiVGI/LivePortrait /LivePortrait",
        f"cd /LivePortrait && git checkout {LP_COMMIT} && mkdir -p pw",
        *[f"wget -q -P /LivePortrait/pw {POIDS}/{f}" for f in FICHIERS],
        f"wget -q -P /LivePortrait/pw {DECOUPE}",
    )
    .add_local_file("essai-generation/tete.py", "/LivePortrait/tete.py")
)

app = modal.App("avirso-tete", image=image)


@app.function(gpu="T4", timeout=900, max_containers=1, scaledown_window=60)
def fabriquer(photos: list[bytes], cote: int = 720) -> dict:
    """Fabrique la suite d'images. `photos` : contenu des fichiers. Renvoie les images (WebP) et leurs angles."""
    import base64, glob, os, re, shutil, subprocess, tempfile, time
    import cv2
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
            cwd="/LivePortrait", capture_output=True, text=True, env={**os.environ, "TAILLE": "1024"},
        )
        journal = [l for l in r.stdout.splitlines() if l.strip()]
        if r.returncode != 0:
            return {"ok": False, "erreur": "le calcul a échoué", "detail": (r.stderr or "")[-800:], "journal": journal[-12:]}
        fichiers = sorted(glob.glob(os.path.join(dossier, "t_[0-9]*.jpg")))
        bornes = None
        for l in journal:
            m = re.search(r"de ([+-][\d.]+)° à ([+-][\d.]+)°", l)
            if m and "images de" in l:
                bornes = (float(m.group(1)), float(m.group(2)))
        if not fichiers or bornes is None:
            return {"ok": False, "erreur": "aucune image produite", "journal": journal[-12:]}
        images = []
        for f in fichiers:
            im = cv2.resize(cv2.imread(f), (cote, cote), interpolation=cv2.INTER_AREA)
            ok, b = cv2.imencode(".webp", im, [cv2.IMWRITE_WEBP_QUALITY, 82])
            images.append(base64.b64encode(b.tobytes()).decode())
        n = len(images)
        angles = [bornes[0] + (bornes[1] - bornes[0]) * k / max(n - 1, 1) for k in range(n)]
        return {"ok": True, "angles": angles, "images": images, "cote": cote, "secondes": round(time.time() - t0, 1),
                "journal": [l for l in journal if "photo" in l or "inclinaison" in l or "hochement" in l][-8:]}
    finally:
        shutil.rmtree(dossier, ignore_errors=True)      # rien n'est gardé


@app.function(max_containers=2)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def site():
    from fastapi import FastAPI, File, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware

    web = FastAPI(title="AVIRSO tête", docs_url=None, redoc_url=None)
    web.add_middleware(CORSMiddleware, allow_origins=ORIGINES, allow_methods=["GET", "POST"], allow_headers=["*"])

    @web.get("/")
    def accueil():
        return {"service": "avirso-tete", "etat": "en marche"}

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
