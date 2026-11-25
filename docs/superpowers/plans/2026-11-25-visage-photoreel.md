# Visage photoréel et essai de coupes par IA — plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** la cliente se reconnaît (rotation à partir de ses vraies photos) et essaie des coupes photoréalistes générées sur ses photos.

**Architecture:** le serveur Modal existant (`serveur-tete/avirso_tete.py`) garde la tournée LivePortrait et reçoit une fonction `retoucher_coupe` (Qwen-Image-Edit-2511) exposée comme la tournée : `POST /coupes` puis `GET /coupes/{id}`. L'app (lot1/web, publiée via /tmp/pub) fait de la tournée le parcours par défaut et branche la rangée « Essayer une coupe » sur ce service.

**Tech Stack:** Python 3.11, Modal, diffusers (Qwen-Image-Edit-2511, bf16), FastAPI ; TypeScript, Vite, three.js ; tests pytest + Playwright (scripts hors dépôt dans /home/claude/parcours).

**Spec:** `docs/superpowers/specs/2026-11-25-visage-photoreel-design.md`

## Global Constraints

- Licences commerciales seulement (Qwen-Image-Edit-2511 : Apache 2.0 ; LivePortrait : MIT). Aucune image web ni de célébrité comme référence.
- Photos et images générées jamais conservées sur le serveur (dossier temporaire supprimé), jamais dans le dépôt public. Les photos de test de Cyrille restent dans /mnt/user-data/uploads.
- Mention sur chaque coupe : « Coupe générée par un modèle sur votre photo : un aperçu, pas une promesse de résultat. »
- Secret Modal : `custom-secret`. Déploiement : lien de test uniquement. Pas de modification de `src/scene.ts`.
- Objectifs : face retouchée < 30 s ; rotation retouchée < 90 s (mesurés à l'étape 0, signalés s'ils ne tiennent pas).
- Commits terminés par les lignes Co-Authored-By / Claude-Session de la session.

## Review Focus

1. Photo de face floue, sombre ou de travers : la retouche doit échouer proprement (message clair, retour à « Ta coupe ») plutôt que rendre un visage déformé.
2. Clics rapides sur plusieurs coupes : une seule demande à la fois, la dernière demandée gagne, aucune image d'une coupe affichée sous l'étiquette d'une autre.
3. Serveur froid (première coupe) : l'attente est annoncée et ne bloque pas les zones ; délai dépassé = message, pas d'écran figé.
4. Identité qui dérive entre la face et les trois-quarts retouchés : contrôle automatique (distance des repères MediaPipe) et repli sur la face seule si la dérive est forte.
5. Personne sans cheveux ou cheveux très courts qui demande « long » : la consigne doit produire une coupe plausible sans toucher barbe ni sourcils.

---

### Task 0: Prototype de validation (porte d'entrée)

**Files:**
- Create: `essai-generation/essai_coupes.py` (point d'entrée `modal run`, lit des chemins de photos passés en argument, écrit les résultats dans un dossier local hors dépôt)
- Create: `serveur-tete/coupes.py` (catalogue et consignes, pur Python)
- Test: `serveur-tete/test_coupes.py`

**Interfaces:**
- Produces: `consigne(coupe: str, couleur: str | None, vue: str) -> str` avec `vue in {"face", "trois_quarts"}` ; `COUPES: dict[str, str]` (clé → description anglaise) ; `COULEURS: dict[str, str]`.
- Produces: fonction Modal `retoucher_coupe(photos: list[bytes], coupe: str, couleur: str | None) -> dict` → `{"ok": bool, "face": str(base64 webp), "vues": list[str], "secondes": float, "erreur"?: str}`.

- [ ] **Step 1: tests du catalogue** — `test_consigne_garde_identite` : la consigne contient « keep the face, skin, beard, eyebrows, lighting and background unchanged » ; `test_consigne_trois_quarts_reference` : pour `vue="trois_quarts"` elle contient « same hairstyle as image 2 » ; `test_coupe_inconnue` : `consigne("xyz", None, "face")` lève `ValueError` ; `test_catalogue` : `set(COUPES) >= {"degrade","court_boucle","afro","tresses","locks","mi_long","long_lisse","long_boucle"}`.
- [ ] **Step 2:** `cd serveur-tete && python -m pytest test_coupes.py -q` → échec (module absent).
- [ ] **Step 3:** écrire `coupes.py` (consignes anglaises, couleur optionnelle ajoutée à la description).
- [ ] **Step 4:** pytest → 4 passés.
- [ ] **Step 5:** ajouter à `avirso_tete.py` une image Modal `image_coupe` (diffusers récent, torch bf16, poids `Qwen/Qwen-Image-Edit-2511` téléchargés à la construction) et `retoucher_coupe` (GPU `H100`, `timeout=600`, `scaledown_window=300`). Méthode : face retouchée seule ; chaque trois-quarts retouché avec `[photo_trois_quarts, face_retouchee]` et la consigne `trois_quarts` ; graine fixe 0.
- [ ] **Step 6:** depuis le Mac (VM `device_bash`) : `modal run essai-generation/essai_coupes.py --photos <3 photos> --coupes degrade,afro,tresses,long_lisse --couleurs noir,chatain` → 8 jeux d'images + temps par appel affichés.
- [ ] **Step 7:** recalculer une tournée sur un jeu retouché (`fabriquer` existant avec les 3 photos retouchées) ; mesurer le temps.
- [ ] **Step 8:** planche comparative envoyée à Cyrille avec temps et coût (coût = secondes GPU × tarif H100 Modal affiché). **Arrêt : on ne poursuit qu'avec son accord.** Refus → revenir à la conception (autre modèle).
- [ ] **Step 9:** commit (`coupes.py`, `test_coupes.py`, `essai_coupes.py`, `avirso_tete.py`), sans aucune image.

### Task 1: Service `/coupes` sur le serveur

**Files:**
- Modify: `serveur-tete/avirso_tete.py` (dans `site()` : routes à côté de `/taches`)
- Test: `serveur-tete/test_coupes.py`

**Interfaces:**
- Consumes: `retoucher_coupe` (Task 0), `COUPES`, `COULEURS`.
- Produces: `POST /coupes` (multipart : `photos` ×3, `coupe`, `couleur` facultatif) → `{"id": str}` ; `GET /coupes/{id}` → `{"etat": "en_cours"}` ou le dict de `retoucher_coupe` ; `POST /reveil` réveille aussi `retoucher_coupe` (appel à vide `photos=[]` → `{"ok": True, "reveil": True}`).

- [ ] **Step 1: tests** — `test_valider_demande` sur une fonction pure `valider_demande(coupe, couleur) -> tuple[str, str | None]` : coupe hors catalogue → `ValueError` ; couleur hors nuancier → `None` ; message tronqué non accepté.
- [ ] **Step 2:** pytest → échec.
- [ ] **Step 3:** `valider_demande` dans `coupes.py` ; routes dans `site()` (spawn + `FunctionCall.from_id`, comme `/taches`) ; `retoucher_coupe` accepte `photos=[]` (réveil).
- [ ] **Step 4:** pytest → passé ; déploiement (`AVEC_ANALYSE=1 SECRET_ANTHROPIC=custom-secret python3 -m modal deploy serveur-tete/avirso_tete.py`) ; `curl -X POST .../reveil` → 200.
- [ ] **Step 5:** commit.

### Task 2: Tournée par défaut, plus nette

**Files:**
- Modify: `lot1/web/src/essai/essai.ts` (choix du parcours après la séance : tournée si l'accord serveur est donné, sinon relief local)
- Modify: `essai-generation/tete.py` (qualité WebP 92 même avec `LEGER=1` ; correction de couleur des images générées vers la photo la plus proche : moyenne et écart-type par canal dans l'espace Lab sur la zone peau)
- Modify: `serveur-tete/avirso_tete.py` (`fabriquer` : `cote` par défaut 960)

**Interfaces:**
- Consumes: `fabriquerTete` / suivi existants (`essai/serveur.ts`).
- Produces: `PERSO.essai.tournee` présent par défaut quand le serveur a répondu.

- [ ] **Step 1:** Playwright `parcours/tournee_defaut.mjs` : séance avec les 3 photos de Cyrille, accord coché → l'aperçu affiche `data-tournee` et la vue de face apparaît avant la fin du calcul ; accord non coché → relief local, aucune requête vers `/taches` (écoute réseau).
- [ ] **Step 2:** lancer → échec.
- [ ] **Step 3:** modifier `essai.ts` ; `tete.py` (correction Lab) ; redéployer.
- [ ] **Step 4:** test → passé ; capture face/trois-quarts comparée côte à côte à la photo d'origine (écart de teinte moyen ΔE < 3 sur la joue, calculé dans le script).
- [ ] **Step 5:** commit (avirso-test) ; lot1 copié dans /tmp/pub.

### Task 3: Essai de coupe dans l'app

**Files:**
- Create: `lot1/web/src/essai/coupesIA.ts`
- Modify: `lot1/web/src/apercu/apercu.ts` (`brancherCoupes` : en mode tournée, utilise `coupesIA` ; en `?tete=mh`, garde la bibliothèque 3D)
- Modify: `lot1/web/src/apercu/apercu.css` (état « en cours » de la puce, mention)

**Interfaces:**
- Consumes: `POST /coupes`, `GET /coupes/{id}` (Task 1) ; les images de la tournée affichées par `tournee3d.ts` (fonction existante de remplacement des images de la tournée).
- Produces: `demanderCoupe(photos: Blob[], coupe: string, couleur: string | null, signal: AbortSignal): Promise<{ face: string; vues: string[] }>` ; cache par clé `coupe|couleur` pour la séance.

- [ ] **Step 1:** Playwright `parcours/coupes_ia.mjs` (serveur réel) : clic « Afro » → la face change en < 30 s, mention visible ; clic « Ta coupe » → images d'origine immédiatement ; clics rapides « Afro » puis « Tresses » → seule la retouche « Tresses » s'affiche (Review Focus 2) ; serveur coupé (route bloquée) → message et puce revenue (Review Focus 3).
- [ ] **Step 2:** lancer → échec.
- [ ] **Step 3:** `coupesIA.ts` (envoi, suivi toutes les 2 s, `AbortSignal`, délai 120 s) ; branchement : face retouchée affichée d'abord, puis tournée retouchée via `fabriquer` sur les 3 photos retouchées ; contrôle d'identité (Review Focus 4) : distance moyenne normalisée des repères MediaPipe face d'origine / face retouchée > 0,04 → on n'affiche que la face, avec une phrase l'expliquant.
- [ ] **Step 3b:** couleur : une deuxième rangée « Couleur » (puces du nuancier `COULEURS`, plus « Ma couleur » = `null`) sous les coupes ; ordre des coupes : celles conseillées par l'analyse d'abord si elle en fournit (aujourd'hui aucune : ordre du catalogue), puis les autres.
- [ ] **Step 4:** test → passé ; captures des 8 coupes envoyées à Cyrille.
- [ ] **Step 5:** commit ; publication sur le lien de test (procédure /tmp/pub habituelle) ; vérification en ligne avec le même script pointé sur le lien de test.

### Task 4: Vérification finale

- [ ] **Step 1:** scripts existants sans régression : `/tmp/verif_demo.mjs`, `parcours/zones_essai.mjs`, `parcours/audit_essai.mjs` → 0 erreur de page.
- [ ] **Step 2:** zones et maillage sur une tournée retouchée (`parcours/zones_mh.mjs` adapté) → carte « Menton » ouverte, voile visible.
- [ ] **Step 3:** compte rendu à Cyrille : fait, temps mesurés, coût par séance et par coupe, limites restantes, test iPhone demandé.
