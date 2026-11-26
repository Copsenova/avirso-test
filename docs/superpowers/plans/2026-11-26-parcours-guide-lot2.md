# Parcours guidé lot 2 — plan de mise en œuvre

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** l'analyse réelle (serveur Modal) produit les chapitres du parcours guidé, et l'espace « essai » les affiche avec le même guide que la démo.

**Architecture :** le conseiller (appel IA existant, sorties structurées) reçoit un bloc de schéma « guide » en plus ; un nouveau module Python `chapitres.py` définit ce schéma et nettoie la réponse (listes fermées, bornes, barbe). Côté app, `attendreAnalyse` transmet `guide`, `essai.ts` le pose dans `__avirsoPerso.guide`, et `apercu.ts` choisit le guide dès qu'un `guide` valide existe (démo ou perso).

**Tech Stack :** Python 3.11 + pytest (serveur `avirso-test/serveur-tete`, déployé sur Modal depuis le Mac) ; TypeScript/Vite (`lot1/web`), tests unitaires Node strip-types, e2e Playwright (`/home/claude/parcours`).

**Spec :** `docs/superpowers/specs/2026-11-26-parcours-guide-lot2-design.md` (et la spec mère `2026-11-26-parcours-guide-design.md`).

## Global Constraints

- Format chapitre identique au lot 1 (`lot1/web/src/apercu/chapitres.ts`) : vu 2–4, sens 1–3, objectif, 3 choix + eviter, routine 3–4, produits ≥ 1.
- Choix pris dans les listes fermées : coupes (catalogue.json, filtrées par texture), barbes (catalogue.json), montures (`visagiste.MONTURES`), couleurs de vêtements (`visagiste.VETEMENTS`). Peau et Regard : texte libre.
- Produits : `cle` uniquement parmi les clés de `lot1/web/src/accueil/exemplesProduits.json` ; aucune marque.
- Pictogrammes uniquement parmi : cheveux peau barbe yeux sourcils levres nez visage coupe couleur routine_jour routine_semaine produits soleil sommeil lunettes vetements outils alimentation.
- Barbe : chapitre présent seulement si `description.barbe.presence` ∈ {naissante, courte, moyenne, longue} ou si `reponses.objectifs` contient `barbe`.
- Tutoiement dans le guide et autour.
- Aucune clé dans le code, le navigateur ou les captures (la clé reste dans le secret Modal). Photos de Cyrille jamais dans le dépôt.
- Déploiement uniquement sur le lien de test (Copsenova/avirso-test, main + gh-pages) et sur l'app Modal existante.
- Commits terminés par les deux lignes d'attribution de la session ; pas de `git add .`.

## Review Focus

1. Réponse de l'IA où un chapitre a deux choix identiques ou un identifiant hors liste → chapitre retiré, jamais affiché à moitié.
2. Texte venant du serveur contenant `<script>` ou des guillemets → affiché comme texte (échappé), y compris dans `data-essai`.
3. Analyse sans `guide` (ancienne analyse gardée sur le téléphone) → affichage actuel, aucune erreur JS.
4. Personne sans barbe visible et sans objectif barbe, mais l'IA a quand même écrit un chapitre barbe → retiré côté serveur ET côté affichage.
5. `guide` présent mais tous les chapitres invalides → affichage actuel (pas de guide vide).

---

### Task 1 : module serveur `chapitres.py` (schéma + nettoyage)

**Files :**
- Create : `avirso-test/serveur-tete/chapitres.py`
- Test : `avirso-test/serveur-tete/test_chapitres.py`

**Interfaces :**
- Consumes : `visagiste.MONTURES`, `visagiste.VETEMENTS`, `visagiste.TEXTURES`, `agents.borner` (importer `borner` depuis un petit déplacement : le copier dans `chapitres.py` pour éviter l'import circulaire).
- Produces :
  - `CONSIGNE: str` (texte ajouté à la consigne du conseiller)
  - `schema(cat: dict) -> dict` (schéma JSON strict du bloc `guide`)
  - `nettoyer_guide(b, cat: dict, description: dict, reponses: dict | None) -> dict | None` → `{"profil": {"barbe": bool}, "ouverture": {"phrases": [str]}, "chapitres": [Chapitre]}` ou `None` si aucune phrase d'ouverture ou aucun chapitre valide.

Forme attendue du bloc renvoyé par l'IA (`b`) : `{"ouverture": [str], "chapitres": {"cheveux": C, "peau": C, "barbe": C, "regard": C, "lunettes": C, "couleurs": C}}` où `C = {"afficher": bool, "vu": [{"texte", "etiquette"}], "sens": [str], "objectif": str, "premier": X, "sur": X, "audacieux": X, "eviter": str, "routine": [{"geste", "detail", "picto"}], "produits": [{"type", "cle"}]}` ; `X = {"id": enum, "pourquoi": str}` pour cheveux/barbe/lunettes/couleurs, `X = {"nom": str, "pourquoi": str}` pour peau/regard. `cle` et `picto` acceptent `""`.

Table fixe côté serveur (titre, picto, zones) : cheveux « Cheveux », cheveux, [hair] ; peau « Peau », peau, [cheeks] ; barbe « Barbe », barbe, [chin, jaw] ; regard « Regard et sourcils », yeux, [eyes, brows] ; lunettes « Lunettes », lunettes, [eyes, nose] ; couleurs « Couleurs », vetements, [neck].

Bornes (mots) : vu.texte 25, etiquette 3, sens 30, objectif 20, pourquoi 30, eviter 30, geste 6, detail 20, type 8, ouverture 30 par phrase (3 phrases max).

- [ ] **Step 1 : écrire les tests** (`test_chapitres.py`), avec une fabrique `bloc(**surcharges)` qui produit une réponse IA complète et valide (6 chapitres, barbe compris) et `CAT` = catalogue.json réel :
  - `test_guide_complet` : description avec barbe « courte » → 6 chapitres dans l'ordre cheveux, peau, barbe, regard, lunettes, couleurs ; `profil == {"barbe": True}` ; noms des choix résolus depuis les listes (ex. monture `wayfarer` → « Wayfarer ») ; cheveux.premier a `essai == "coupe"`.
  - `test_barbe_retiree_sans_barbe_visible` : presence « aucune », objectifs [] → pas de chapitre barbe, `profil.barbe is False`.
  - `test_barbe_gardee_si_objectif_barbe` : presence « indéterminé », objectifs ["barbe"] → chapitre barbe présent.
  - `test_identifiant_inconnu_retire_le_chapitre` : lunettes.premier.id = "licorne" → pas de chapitre lunettes, les autres restent.
  - `test_choix_en_double_retire_le_chapitre` : couleurs premier et sur = "marine" → pas de chapitre couleurs.
  - `test_coupe_incompatible_avec_la_texture` : texture « crépus », cheveux.premier = une coupe dont `textures` ne contient pas `crepu` → chapitre cheveux retiré.
  - `test_afficher_faux` : peau.afficher = False → pas de chapitre peau.
  - `test_bornes` : vu de 6 éléments → 4 gardés ; texte de 60 mots → ≤ 25 mots ; routine de 6 → 4 ; routine de 2 → chapitre retiré.
  - `test_cle_et_picto_hors_liste` : produit cle « marque-x » → produit gardé sans `cle` ; picto « licorne » → geste gardé sans `picto`.
  - `test_aucun_chapitre_valide` et `test_ouverture_vide` → `None`.
  - `test_schema_strict` : `schema(CAT)` a `additionalProperties: False` partout et l'enum de cheveux.premier.id égale les ids du catalogue.
- [ ] **Step 2 : lancer** `cd avirso-test/serveur-tete && python3 -m pytest test_chapitres.py -q` — attendu : ÉCHEC (module absent).
- [ ] **Step 3 : écrire `chapitres.py`** selon les interfaces ci-dessus. `CONSIGNE` demande : tutoiement, voix du visagiste du lot 1 (« Ce que je vois »…), 3 phrases d'ouverture (forme du visage, cheveux, peau et sous-ton), chaque constat tiré de la description sans rien inventer, propositions tirées des fiches et des listes, coupe compatible avec la texture, `afficher: false` pour un chapitre sans matière fiable (et pour la barbe sans barbe visible ni objectif barbe), produits par `cle` de la liste fournie, aucune marque, savoir-faire et tendances jamais présentés comme des faits.
- [ ] **Step 4 : relancer** les tests — attendu : tous OK ; puis `python3 -m pytest -q` (toute la suite serveur) — attendu : OK.
- [ ] **Step 5 : commit** `git add serveur-tete/chapitres.py serveur-tete/test_chapitres.py` — « feat(serveur): chapitres du parcours guidé (schéma et nettoyage) ».

### Task 2 : le conseiller écrit le guide

**Files :**
- Modify : `avirso-test/serveur-tete/agents.py` (fonction `analyser`)
- Modify : `avirso-test/serveur-tete/avirso_tete.py` (copie de `chapitres.py` dans l'image Modal, comme `visagiste.py`)
- Test : `avirso-test/serveur-tete/test_agents.py`

**Interfaces :**
- Consumes : `chapitres.CONSIGNE`, `chapitres.schema`, `chapitres.nettoyer_guide`.
- Produces : la réponse de `analyser` gagne la clé `guide` (dict ou `None`). Quand `styles` est fourni : la consigne devient `CONSIGNE_CONSEILLER + CONSIGNE_VISAGISTE + chapitres.CONSIGNE`, le schéma gagne la propriété requise `guide`, budget de jetons 20000.

- [ ] **Step 1 : test** `test_analyser_renvoie_le_guide` : faux client dont `messages.create` renvoie d'abord une description (barbe « aucune », texture « raides ») puis un conseil complet avec `visagiste` et `guide` (fabrique de `test_chapitres`) ; `analyser(client, [jpeg_minuscule], catalogue, None, styles=CAT)` → `r["guide"]["chapitres"]` sans barbe, et le schéma passé au second appel contient `guide` dans `required`.
- [ ] **Step 2 :** `python3 -m pytest test_agents.py -q` — attendu : ÉCHEC.
- [ ] **Step 3 :** brancher `chapitres` dans `analyser` ; ajouter `chapitres.py` aux fichiers copiés dans l'image de `avirso_tete.py`.
- [ ] **Step 4 :** suite serveur complète — attendu : OK.
- [ ] **Step 5 : commit** « feat(serveur): le conseiller écrit le parcours guidé ».

### Task 3 : l'espace essai affiche le guide

**Files :**
- Modify : `lot1/web/src/essai/serveur.ts` (`AnalyseIA`, `attendreAnalyse`)
- Modify : `lot1/web/src/essai/essai.ts` (`ouvrir` : `guide` dans `__avirsoPerso`, mention au tutoiement quand il y a un guide)
- Modify : `lot1/web/src/apercu/apercu.ts` (type `Perso`, choix du guide, libellés perso au tutoiement quand GUIDE)
- Modify : `lot1/web/src/apercu/vueChapitres.ts` (échappement de `data-essai` limité à coupe/couleur/lunettes ; lien d'exemple seulement en `https?://`)
- Create : `/home/claude/parcours/fixture_perso_guide.js` (analyse réelle simulée : guide de 5 chapitres sans barbe, un texte contenant `<img src=x onerror=alert(1)>`, un `essai` piégé `coupe" onclick="x`)
- Modify : `/home/claude/parcours/parcours_guide.mjs`

**Interfaces :**
- Consumes : le JSON `guide` de la Task 2 (`{profil, ouverture, chapitres}`).
- Produces : `type GuideIA = { profil: Profil; ouverture: Ouverture; chapitres: Chapitre[] }` exporté par `essai/serveur.ts` ; `AnalyseIA.guide?: GuideIA | null` et `AnalyseIA.visagiste` désormais transmis ; `Perso.guide?: GuideIA | null`.
- Règle dans apercu.ts : `SOURCE_G = PERSO ? PERSO.guide ?? null : DEMO_G` ; `CHAPITRES = SOURCE_G ? chapitresPour(SOURCE_G.profil, SOURCE_G.chapitres) : []` ; `GUIDE = CHAPITRES.length > 0`.

- [ ] **Step 1 : tests e2e** dans `parcours_guide.mjs`, mode `--demo`, nouvelle variable `PERSO_GUIDE_FIXTURE` :
  - « perso avec guide : le guide est affiché » (`#ens .gd` présent, ouverture affichée) ;
  - « perso avec guide : pas de barbe » ;
  - « perso avec guide : texte du serveur échappé » (aucun `img[src="x"]` dans `.gd`, le texte `<img` visible tel quel) ;
  - « perso avec guide : data-essai filtré » (aucun attribut `onclick` dans `.gd`) ;
  - « perso avec guide : tutoiement autour du guide » (même expression que la démo) ;
  - « perso avec guide : aucune erreur JS ».
  Le test perso existant (« affichage actuel conservé ») reste : il couvre une analyse sans guide.
- [ ] **Step 2 :** lancer `node parcours_guide.mjs http://127.0.0.1:5173 --demo` avec `PERSO_FIXTURE` et `PERSO_GUIDE_FIXTURE` — attendu : ÉCHEC des nouveaux contrôles.
- [ ] **Step 3 :** implémenter les modifications listées ; `npx tsc --noEmit` — attendu : aucune erreur.
- [ ] **Step 4 :** suite complète : unitaires (`chapitres`, `demoChapitres`), `parcours_guide.mjs` (seul et `--demo`), `lot1_accueil.mjs`, `capture_coach.mjs` — attendu : tout OK.
- [ ] **Step 5 :** publier (`publier.sh`), commit « feat: l'analyse réelle s'affiche en parcours guidé », push main + gh-pages, attendre le nouvel asset en ligne, relancer `parcours_guide.mjs https://copsenova.github.io/avirso-test --demo` — attendu : OK.

### Task 4 : déploiement Modal et vrai essai

**Files :** aucun fichier du dépôt ; script d'essai privé dans `~/Desktop/avirso-photos-privees/` sur le Mac (jamais dans le dépôt).

- [ ] **Step 1 :** copier `agents.py`, `chapitres.py` et `avirso_tete.py` à jour sur le Mac (dossier de déploiement habituel) ; `modal deploy avirso_tete.py` — attendu : déploiement réussi.
- [ ] **Step 2 :** appeler `analyser_photos` avec les 3 photos privées de Cyrille (accord du 25/11) ; enregistrer la réponse dans le dossier privé ; noter `secondes`.
- [ ] **Step 3 :** vérifier : `guide` non nul, chapitres présents et cohérents avec la description, barbe présente seulement si visible, aucun vouvoiement, aucune marque ; noter l'écart de durée par rapport à une analyse sans guide si une mesure antérieure existe, sinon donner la durée seule.
- [ ] **Step 4 :** afficher cette vraie réponse dans l'app en local (fixture privée hors dépôt) et regarder les écrans ; ne rien publier qui contienne ses données.
