# Réponses rangées, pictogrammes en points, achat partenaire — plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** l'IA renvoie 3 à 5 sujets rangés, affichés un à un avec un pictogramme en points, jusqu'à un écran « Ce qu'il vous faut » relié aux offres partenaires.

**Architecture:**
- **Serveur :** le conseiller (`serveur-tete/agents.py`) change de schéma de sortie.
- **App (`lot1/web`) :** elle lit le nouveau format, ou l'ancien en repli, et l'affiche dans le panneau bilan.
- **Pictogrammes :** les symboles de zone (`apercu/symboles.ts`, même API `data-sym`) deviennent des pictogrammes en points.
- **Offres partenaires :** elles viennent du deuxième cerveau (`partenaires.json`).

**Tech Stack:** Python 3 (pytest), Modal ; TypeScript, Vite ; Playwright (scripts dans /home/claude/parcours).

**Spec:** `docs/superpowers/specs/2026-11-25-reponses-structurees-design.md`

## Global Constraints

- Sujets : 3 à 5. Accroche : 30 mots au plus. Constat, conséquence et action : 25 mots au plus chacun. Titre : 2 à 4 mots.
- Pictogrammes : grille de 9 × 9 points, 40 px (24 px en liste). Balayage d'allumage d'environ 1 s, puis fixe. Léger passage toutes les 8 à 12 s sur le sujet affiché seulement. Rien si l'option « réduire les mouvements » est active. Pas de rouge.
- Liste fermée des pictogrammes : cheveux, peau, barbe, yeux, sourcils, levres, nez, visage, coupe, couleur, routine_jour, routine_semaine, produits, soleil, sommeil, alimentation.
- Offre partenaire : mention exacte « Lien partenaire : AVIRSO peut toucher une commission ». Sans offre enregistrée : « Sélection partenaire bientôt disponible ». Aucun produit fictif.
- Natures des fiches et règles d'honnêteté de l'agent inchangées. Thème clair et verre liquide existants.

## Review Focus

1. Réponse IA à l'ancien format (texte + points) ou absente : le bilan affiche quand même des sujets, construits à partir des points ou des zones.
2. Sujet dont la zone n'existe pas sur le modèle : le sujet reste lisible, et le bouton « Voir sur le visage » est masqué.
3. Mouvement réduit : les pictogrammes sont dessinés allumés, sans aucune animation.
4. Une seule offre partenaire, pour un type de produit absent des sujets : elle ne s'affiche pas.
5. « Suivant » au dernier sujet : on arrive sur « Ce qu'il vous faut ». « Tout voir » puis retour garde le sujet courant.

---

### Task 1: Agent conseiller au nouveau format

**Files:**
- Modify: `serveur-tete/agents.py` (consigne du conseiller, `SCHEMA_CONSEILLER`, `nettoyer`)
- Create: `serveur-tete/test_agents.py`

**Interfaces:**
- Produces: `nettoyer(conseil, catalogue) -> {"accroche": str, "sujets": [{"pictogramme","titre","constat","consequence","action","zone","fiches":[int],"produit": str|None}], "suite": str, "selection": [...], "points": [...]}`. `points` est dérivé des sujets (titre, constat, zone) pour les anciennes versions de l'app.
- Produces: `PICTOGRAMMES: list[str]` (la liste fermée).

- [ ] **Step 1: tests** dans `test_agents.py` :
  - `test_sujets_tronques_et_limites` : 7 sujets donnés → 5 gardés ; un constat de 60 mots → 25 mots au plus.
  - `test_pictogramme_inconnu` : un pictogramme inconnu est remplacé par `"visage"`.
  - `test_fiches_hors_catalogue_retirees`.
  - `test_points_derives` : `len(points) == len(sujets)`.
  - `test_accroche_vide_refusee` : lève `ValueError`.
- [ ] **Step 2:** `cd serveur-tete && python3 -m pytest test_agents.py -q` → échec.
- [ ] **Step 3:**
  - consigne : la tâche 2 devient « accroche + sujets ordonnés (objectif d'abord) + suite » ;
  - schéma strict : `pictogramme` est un enum fermé, `produit` est une chaîne vide si aucun ;
  - `nettoyer` applique les limites.
- [ ] **Step 4:** pytest → passé.
- [ ] **Step 5:** déploiement Modal et commit.

### Task 2: Pictogrammes en points

**Files:**
- Rewrite: `lot1/web/src/apercu/symboles.ts` (même API : `surveillerSymboles()`, attribut `data-sym`)
- Modify: `lot1/web/src/apercu/apercu.css` (tailles `.ap-sym`)
- Test: `parcours/pictos.mjs`

**Interfaces:**
- Produces: `type Picto` (liste fermée) ; `pictoDeZone(zone: string): Picto` (forehead → cheveux, cheeks → peau, chin et jaw → barbe, etc.) ; `data-sym` accepte une zone ou un `Picto`.

- [ ] **Step 1: test Playwright** sur `essai.html?tete=mh` jusqu'à l'aperçu :
  - chaque `[data-sym] canvas` a au moins 20 pixels non transparents après 2 s ;
  - aucune image d'animation pendant 1,5 s après le balayage, sauf le léger passage (on compte les `requestAnimationFrame` actifs, 0 attendu hors passage) ;
  - avec `reducedMotion: 'reduce'`, le dessin est complet dès la première image.
- [ ] **Step 2:** lancer → échec (anciens symboles en particules).
- [ ] **Step 3:** réécrire `symboles.ts` :
  - chaque dessin est un tableau de 9 chaînes de 9 caractères (`.` = point éteint, une lettre = une famille de couleur) ;
  - le dessin se fait en canevas ;
  - le balayage s'allume ligne par ligne en environ 1 s, au premier passage dans l'écran (observateur de visibilité) ;
  - le passage léger revient toutes les 8 à 12 s, uniquement sur un élément marqué `data-actif`.
- [ ] **Step 4:** test → passé. Capture des 16 pictogrammes en planche.
- [ ] **Step 5:** commit.

### Task 3: Données du bilan (parcours) et offres

**Files:**
- Modify: `lot1/web/src/accueil/contenuPerso.ts`, `lot1/web/src/essai/serveur.ts` (type `AnalyseIA`)
- Create: `lot1/web/src/accueil/parcours.ts`, `lot1/web/src/accueil/partenaires.json` (tableau vide)
- Modify: `cerveau-avirso/construire.py` (commande `partenaires` : table `offres_partenaires`, note, export `partenaires.json`) ; Create: `cerveau-avirso/test_partenaires.py`

**Interfaces:**
- Produces: `type Sujet = { picto: Picto; titre: string; constat: string; consequence: string; action: string; zone: RegionId | null; produit: ProduitId | null }`.
- Produces: `type Parcours = { accroche: string; sujets: Sujet[]; suite: string }`.
- Produces: `construireParcours(ia: AnalyseIA | null, zones, releves): Parcours`. Ordre de repli : nouveau format, puis ancien format (points), puis zones relevées (3 premières).
- Produces: `offresPour(produits: ProduitId[]): Offre[]`.
- Produces: `BILAN.parcours`.
- Produces: `type Offre = { partenaire, nom, produit, prix, url, releve }`.

- [ ] **Step 1: tests**
  - pytest `test_partenaires.py` : `construire.py partenaires` crée la table et exporte `[]` sans offre ; une offre de test donne le bon JSON.
  - Playwright : `window.__avirsoParcours` existe sur l'aperçu et compte entre 3 et 5 sujets.
- [ ] **Step 2:** lancer → échec.
- [ ] **Step 3:** implémenter (`parcours.ts` pur, appelé par `contenuPerso.ts`).
- [ ] **Step 4:** tests → passés. Synchroniser le cerveau sur le Mac et lancer `python3 construire.py partenaires`.
- [ ] **Step 5:** commit.

### Task 4: Affichage un sujet à la fois

**Files:**
- Modify: `lot1/web/src/apercu/apercu.ts` (panneau bilan `#ens`), `lot1/web/src/apercu/apercu.css`
- Test: `parcours/parcours_bilan.mjs`

**Interfaces:**
- Consumes: `BILAN.parcours`, `offresPour`, `pictoDeZone`.

- [ ] **Step 1: test Playwright**
  - Le bilan ouvert affiche l'accroche et un seul `.pc-sujet` visible, avec son `[data-sym]` et ses 3 lignes.
  - La barre `.pc-points` indique « 1 / n ». « Suivant » amène à 2 / n.
  - Au dernier sujet, « Suivant » ouvre `.pc-fin` « Ce qu'il vous faut », qui contient « Sélection partenaire bientôt disponible ».
  - « Tout voir » montre tous les sujets. Revenir garde le sujet courant.
  - « Voir sur le visage » sélectionne la zone et ouvre sa carte.
  - Aucune erreur de page.
- [ ] **Step 2:** lancer → échec.
- [ ] **Step 3:**
  - remplacer le texte d'un bloc du bilan par le parcours ;
  - le guide écrit « On passe à <titre> » à chaque changement ;
  - le marquage `data-actif` va sur le pictogramme du sujet affiché ;
  - l'écran de fin liste les actions et les types de produits, puis les offres avec la mention partenaire (ou la phrase « bientôt disponible »).
- [ ] **Step 4:** test → passé. Captures envoyées à Cyrille.
- [ ] **Step 5:** commit, publication sur le lien de test (procédure /tmp/pub), puis vérification en ligne avec le même script.
