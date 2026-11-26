# Parcours visagiste guidé — Lot 1 (démo) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer, dans la démo, les onglets Bilan / Visagiste et la liste des 12 zones par un parcours guidé par chapitres (4 écrans chacun) terminé par une fiche.

**Architecture:** Un module pur `apercu/chapitres.ts` (types, filtre par profil, validation) ; des données de démo `accueil/demoChapitres.json` réécrites pour le mannequin féminin ; un module d'affichage `apercu/vueChapitres.ts` (HTML + navigation) branché dans `apercu.ts` à la place du panneau `#ens` en mode démo. Le mode analyse réelle (`PERSO`) garde l'affichage actuel jusqu'au lot 2.

**Tech Stack:** TypeScript, Vite, three.js (inchangé), Playwright (tests de parcours), Node 22 (exécution directe des `.ts` pour les tests unitaires).

**Spec:** `docs/superpowers/specs/2026-11-26-parcours-guide-design.md` ; maquettes validées https://claude.ai/artifact/5ZqTDBXuV73eF1aTgwoymQ

## Global Constraints

- Code source dans `/home/claude/lot1/web/src` ; publication uniquement par `/home/claude/outils/publier.sh` vers Copsenova/avirso-test (`main` + `gh-pages`), puis commit dans `/home/claude/avirso-test` avec les deux lignes d'attribution.
- Tutoiement dans tout le parcours guidé.
- Design conservé : `ui/clair.css` (dégradé, verre, Doto, Geist Mono), pictogrammes `apercu/symboles.ts` via `<span class="ap-sym" data-sym="…">`.
- Aucun produit, marque, prix ou chiffre inventé : les exemples viennent de `accueil/exemplesProduits.json` ; les choix (coupes, couleurs, montures, couleurs de vêtements) viennent des listes existantes.
- Pas de chapitre Barbe ni d'outil de barbe pour un profil sans barbe ; aucun chapitre vide.
- Un seul bouton principal par écran ; au plus 4 idées par écran.
- Ne pas modifier `src/scene.ts`. Pas de synthèse vocale.
- Animation d'écriture coupée si `prefers-reduced-motion: reduce`.

## Review Focus

1. Profil sans barbe : aucun mot « barbe », « tondeuse », « moustache » visible nulle part dans la démo (chapitres, fiche, routine) → test e2e « aucune barbe ».
2. Retour arrière et saut de chapitre : « ← » à l'écran 1 d'un chapitre ramène au chapitre précédent (écran 4) ou à l'ouverture ; « Passer ce chapitre » va au suivant sans perdre la fiche → test e2e navigation.
3. Toucher une zone du visage 3D pendant le parcours ouvre le bon chapitre à l'écran 1 (cheveux → Cheveux, joues/nez → Peau, yeux/sourcils → Regard) → test e2e raccourci.
4. Mode analyse réelle (`window.__avirsoPerso`) : l'ancien affichage reste intact (pas de régression pour les clients payants) → test e2e perso inchangé.
5. Écran étroit (320 px) et clavier : boutons ≥ 44 px, focus visible, `aria-live` annonce l'étape → test e2e à 320 px.

---

### Task 1: Modèle de chapitre et filtre par profil

**Files:**
- Create: `lot1/web/src/apercu/chapitres.ts`
- Test: `lot1/web/tests/chapitres.unit.mjs`

**Interfaces:**
- Produces:
  - `type Profil = { genre?: 'femme' | 'homme' | 'autre'; barbe?: boolean }`
  - `type Choix = { id: string; nom: string; pourquoi: string; essai?: 'coupe' | 'couleur' | 'lunettes' }`
  - `type Chapitre = { id: 'cheveux' | 'peau' | 'barbe' | 'regard' | 'lunettes' | 'couleurs'; titre: string; picto: string; zones: string[]; vu: { texte: string; etiquette?: string }[]; sens: string[]; objectif: string; conseils: { premier: Choix; sur: Choix; audacieux: Choix; eviter: string }; routine: { geste: string; detail: string; picto?: string }[]; produits: { type: string; cle?: string }[] }`
  - `type Ouverture = { phrases: string[] }`
  - `function chapitresPour(profil: Profil, chapitres: Chapitre[]): Chapitre[]` — ordre fixe cheveux, peau, barbe, regard, lunettes, couleurs ; retire `barbe` sauf si `profil.barbe === true` ; retire tout chapitre invalide.
  - `function erreursChapitre(c: Chapitre): string[]` — liste vide si valide : 2–4 `vu`, 1–3 `sens`, `objectif` non vide, 3 choix nommés + `eviter`, 3–4 `routine`, ≥1 `produits`.

- [ ] **Step 1: Write the failing test** (`tests/chapitres.unit.mjs`, exécuté par `node tests/chapitres.unit.mjs`, assertions `node:assert/strict`) :
  - `chapitresPour({genre:'femme'}, [barbe, cheveux, peau])` → ids `['cheveux','peau']`.
  - `chapitresPour({barbe:true}, [barbe, cheveux])` → ids `['cheveux','barbe']`.
  - un chapitre avec `vu: []` → absent du résultat et `erreursChapitre` contient `"vu"`.
  - un chapitre avec 5 gestes → `erreursChapitre` contient `"routine"`.
- [ ] **Step 2: Run** `cd /home/claude/lot1/web && node tests/chapitres.unit.mjs` — Expected: FAIL (module introuvable).
- [ ] **Step 3: Implement** `chapitres.ts` (aucun import, pour rester exécutable par Node).
- [ ] **Step 4: Run** the same command — Expected: `OK 4 tests`.

### Task 2: Données de démo cohérentes avec le mannequin

**Files:**
- Create: `lot1/web/src/accueil/demoChapitres.json`
- Test: `lot1/web/tests/demoChapitres.unit.mjs`

**Interfaces:**
- Consumes: `erreursChapitre`, `chapitresPour` (Task 1).
- Produces: JSON `{ "profil": {"genre":"femme","barbe":false}, "ouverture": {"phrases":[3 phrases]}, "chapitres": Chapitre[] }` avec les chapitres `cheveux, peau, regard, lunettes, couleurs`.

Faits du mannequin (repris de `accueil/contenu.ts`, seule source) : front haut ; pommettes hautes, joues pleines, mâchoire douce, menton arrondi (visage ovale à doux) ; peau claire à grain fin, taches de rousseur sur le haut des joues et le nez, légère coloration des pommettes à confirmer ; iris noisette, œil en amande, légère ombre sous l'œil ; sourcils fournis brun foncé, arche douce, posés près de l'œil ; cheveux brun foncé uniforme, reflets froids, lisses, fibre moyenne, mi-longs, plaqués en arrière et attachés bas tous les jours ; lèvres pleines rose naturel. Choix pris dans les listes existantes : coupes de `COUPES` (apercu.ts) et du catalogue serveur, montures de `visagiste.py` (MONTURES), couleurs de vêtements de `visagiste.py` (VETEMENTS, avec hex), produits = clés de `exemplesProduits.json`. Contenu attendu par chapitre : Cheveux (tirage quotidien → racines fragilisées ; conseils coupe + « éviter : chignon serré au même endroit chaque jour » ; routine shampoing doux, après-shampoing longueurs, élastiques sans métal / taie satin) ; Peau (taches de rousseur, peau claire → protection solaire quotidienne ; nettoyant doux, crème céramides, SPF50) ; Regard (sourcils, ombre sous l'œil à confirmer ; gel sourcils, correcteur) ; Lunettes (montures adaptées aux sourcils bas et au visage doux, essai `lunettes`) ; Couleurs (couleurs de vêtements de la liste, en accord avec iris noisette et cheveux brun foncé).

- [ ] **Step 1: Write the failing test** : charge le JSON ; `chapitresPour(profil, chapitres)` renvoie 5 chapitres dans l'ordre ; chaque `erreursChapitre` est vide ; aucun texte (JSON sérialisé, en minuscules) ne contient `barbe`, `tondeuse`, `moustache`, ` vous `, `votre`, `vos ` ; chaque `produits[].cle` existe dans `exemplesProduits.json` ; `ouverture.phrases.length === 3`.
- [ ] **Step 2: Run** `node tests/demoChapitres.unit.mjs` — Expected: FAIL (fichier absent).
- [ ] **Step 3: Write** `demoChapitres.json` (tutoiement, phrases courtes, chaque « pourquoi » relié à un trait du mannequin).
- [ ] **Step 4: Run** — Expected: `OK`.

### Task 3: Affichage guidé et navigation

**Files:**
- Create: `lot1/web/src/apercu/vueChapitres.ts`
- Modify: `lot1/web/src/ui/clair.css` (styles `.gd-*`)
- Test: `/home/claude/parcours/parcours_guide.mjs` (Playwright, page de test `?guide=seul` qui affiche le parcours sans le reste de la démo)

**Interfaces:**
- Consumes: `Chapitre`, `Ouverture` (Task 1) ; données (Task 2) ; `Picto`/`data-sym` (symboles.ts) ; `exemplesDe(cle)` déplacé depuis apercu.ts vers `vueChapitres.ts` et ré-exporté.
- Produces:
  - `function htmlGuide(o: { ouverture: Ouverture; chapitres: Chapitre[] }): string`
  - `function brancherGuide(racine: HTMLElement, o: { chapitres: Chapitre[]; surZone?(zones: string[]): void; surEssai?(c: Choix): void; reduit: boolean }): { allerChapitre(id: Chapitre['id']): void }`
  - Écrans : ouverture (`data-ecran="ouverture"`), puis pour chaque chapitre `data-ecran="<id>-1"` … `"<id>-4"`, puis `data-ecran="fiche"`. Un seul visible à la fois. En-tête : `← `, « Chapitre N · Titre », `k/4`, 4 points. Bouton principal : « Qu'est-ce que ça veut dire ? », « Qu'est-ce que tu me conseilles ? », « Ta routine », « Chapitre suivant : … » / « Voir ma fiche ». Lien secondaire « Passer ce chapitre ». Écran 3 : bouton « Essayer sur moi » si `premier.essai`. Écran 4 : chaque produit ouvre ses exemples (`<details>`). Fiche : pour chaque chapitre, le premier choix, l'objectif, la routine en une ligne, la liste des types de produits.
  - `aria-live="polite"` annonce « Chapitre N, étape k sur 4 » ; le titre de l'écran reçoit le focus.

- [ ] **Step 1: Write the failing e2e test** `parcours_guide.mjs` (base URL en argument, `?guide=seul`) : ouverture visible avec 3 phrases et 5 chapitres listés ; Suivant ×4 parcourt Cheveux 1→4 (titres « Ce que je vois. », « Ce que ça veut dire. », « Ce que je te conseille. », « Ta routine. ») ; écran 3 = 3 choix + « À éviter » ; écran 4 = 3–4 gestes + ≥1 produit dont les exemples s'ouvrent ; « ← » depuis Peau-1 → Cheveux-4 ; « Passer ce chapitre » depuis Cheveux-1 → Peau-1 ; après le dernier chapitre la fiche liste 5 chapitres ; aucun texte visible ne contient barbe/tondeuse/moustache ; à 320 px de large tous les boutons font ≥ 44 px de haut ; avec `reducedMotion: 'reduce'` le texte est entier immédiatement.
- [ ] **Step 2: Run** `node /home/claude/parcours/parcours_guide.mjs http://127.0.0.1:5173` (serveur vite relancé si besoin) — Expected: FAIL (`?guide=seul` sans parcours).
- [ ] **Step 3: Implement** `vueChapitres.ts`, styles `.gd-*` (verre `--cl-verre`, relief `--cl-relief`, titres Doto, pictogrammes `ap-sym`) et la page de test `?guide=seul` dans `apercu.ts` (rend seulement `htmlGuide`).
- [ ] **Step 4: Run** — Expected: `FIN` avec tous les contrôles OK.

### Task 4: Branchement dans la démo, publication

**Files:**
- Modify: `lot1/web/src/apercu/apercu.ts` (panneau `#ens`, `selectionner`, bouton Plan, liste des zones)
- Modify: tests existants qui cliquent sur les onglets Bilan/Visagiste ou la liste des zones (`/home/claude/parcours/lot1_accueil.mjs`, `visagiste.mjs`, `exemples.mjs`)
- Test: `/home/claude/parcours/parcours_guide.mjs` (cas démo complète + perso)

**Interfaces:**
- Consumes: `htmlGuide`, `brancherGuide`, `chapitresPour`, `demoChapitres.json`.
- Produces: en démo (`!PERSO`), `#ens-corps` contient le guide ; plus d'onglets `[data-ens-onglet]` ni de bouton « Choisir une zone » ; le bouton flottant devient « Ma fiche » et ouvre l'écran fiche ; toucher le visage appelle `allerChapitre` selon la table : `hair→cheveux`, `cheeks|nose|forehead|temples|mouth|chin|jaw→peau`, `eyes|brows→regard`, `ears→lunettes`, `neck→couleurs`. « Essayer sur moi » réutilise le gestionnaire d'essai existant (`#styles-ouvrir` + onglet) pour `coupe`/`couleur`, et montre l'essai des montures pour `lunettes` s'il existe, sinon le bouton est absent. En mode `PERSO`, rien ne change.

- [ ] **Step 1: Extend the e2e test** : sur la démo réelle (`/`), le guide est dans `#ens` ; absence de `[data-ens-onglet]` et de `#choisir` ; clic sur la zone cheveux (DOM `[data-z="hair"]` conservé pour le raccourci accessible, ou toucher simulé) → écran `cheveux-1` ; « Ma fiche » → écran fiche ; avec `window.__avirsoPerso` injecté (fixture existante des tests perso), les onglets Bilan/Visagiste sont toujours là.
- [ ] **Step 2: Run** — Expected: FAIL sur la démo.
- [ ] **Step 3: Implement** le branchement ; mettre à jour les tests existants pour le nouveau chemin.
- [ ] **Step 4: Run** `parcours_guide.mjs`, `lot1_accueil.mjs`, `visagiste.mjs`, `exemples.mjs`, `capture_coach.mjs` — Expected: tous `FIN` sans échec.
- [ ] **Step 5: Publish** : `bash /home/claude/outils/publier.sh`, commit dans `/home/claude/avirso-test` (`git add` des fichiers listés par le script, jamais `git add .`), `git push -q origin main main:gh-pages`, attendre le nouveau hash en ligne, relancer `parcours_guide.mjs https://copsenova.github.io/avirso-test` — Expected: `FIN`.
