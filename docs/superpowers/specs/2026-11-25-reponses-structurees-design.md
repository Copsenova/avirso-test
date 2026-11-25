# AVIRSO — Réponses rangées, sujets séparés, pictogrammes en points, achat partenaire (conception)

Date : 25/11/2026 · Statut : à valider par Cyrille

## 1. Intention

La personne se perd : la réponse de l'IA se lit comme un pavé. Cyrille veut que tout **découle** :
1. d'abord ce que la personne est venue comprendre,
2. puis ce qui en découle,
3. puis une suite claire, jusqu'à l'achat de produits de marques partenaires.

Chaque sujet est un bloc court, avec une **coupure nette** entre deux sujets, signalée par un pictogramme. On garde le même principe : le visage s'affiche, on touche une zone, la suite arrive. L'IA peut accompagner la lecture.

## 2. Audit du parcours actuel (lu dans le code et le deuxième cerveau, 25/11)

| Constat | Effet sur la personne | Correction prévue |
|---|---|---|
| L'IA écrit un texte libre (jusqu'à 1 600 caractères), affiché d'un bloc dans le bilan | Lecture de « dissertation », on décroche | Réponse en 3 à 5 sujets courts, chacun en 3 lignes au plus |
| Seul le 1er point est relié à l'objectif de la personne ; les autres arrivent sans ordre | On ne voit pas où l'on va | Sujets classés par priorité : objectif déclaré d'abord, puis ce qui en découle |
| Beaucoup d'entrées en même temps : bilan, 12 zones, essai de style, 5 questions, plan, synthèse | Trop de choix, on ne sait pas par où commencer | Un fil principal (« Suivant ») ; le reste reste accessible mais secondaire |
| Les zones s'ouvrent déjà en entonnoir (zone → ce qu'on voit → ce qu'on peut faire → type de produit) | Bonne base, mais elle arrive après le pavé | On garde l'entonnoir, au même format de bloc que le bilan |
| Les produits sont des types sans marque ni lien ; « Mon plan » liste sans permettre d'acheter | Aucune suite concrète | Bloc final « Ce qu'il vous faut », avec les offres partenaires quand elles existent |
| Symboles de zones en particules, différents du reste de l'interface | Langage visuel incohérent | Un seul système de pictogrammes en points, partout |

## 3. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
1. Réponse de l'IA rangée :
   - une phrase d'accroche qui répond à ce que la personne est venue chercher ;
   - 3 à 5 sujets, chacun en « ce qu'on voit → ce que ça change → ce que vous pouvez faire » ;
   - une suite.
2. Une coupure visible entre les sujets : bloc séparé, pictogramme qui s'allume, passage au sujet suivant par « Suivant ».
3. Pictogrammes en points (style petit écran à LED) :
   - abstraits, quelques couleurs discrètes, un carré de taille fixe ;
   - ils s'allument progressivement à l'arrivée, puis restent calmes ;
   - un par sujet (cheveux, peau, barbe, coupes, couleur, routine jour ou semaine, produits, etc.).
4. La même mise en forme pour le bilan, les zones et la synthèse.
5. Une suite d'achat. Tout produit proposé est rattaché à un sujet constaté sur le visage, avec la mention « lien partenaire ».

**Non-objectifs (ce lot)**
- Panier et paiement sur AVIRSO (piste B, plus tard).
- Négocier les partenariats (Cyrille).

**Anti-objectifs**
- Un produit poussé sans lien avec ce qu'on a vu sur le visage.
- Un lien commercial non signalé.
- Inventer des produits, des prix ou des marques.
- Une animation qui clignote en permanence ou fatigue l'œil.

## 4. Contraintes

- Les conseils restent sourcés : les natures des fiches (prouvé, études, savoir-faire, etc.) et leurs mentions sont gardées.
- Liens commerciaux identifiés comme tels (« Lien partenaire : AVIRSO peut toucher une commission »).
- Thème clair et verre liquide actuels. Polices Doto (titres) et Geist Mono.
- Mouvement réduit respecté : le pictogramme reste fixe si la personne l'a demandé.
- Le serveur de l'IA garde des sorties structurées (schéma JSON) et des longueurs plafonnées côté serveur.

## 5. Approches

| | Principe | Pour | Contre |
|---|---|---|---|
| **1. L'IA renvoie directement des sujets structurés (retenue)** | Le schéma de réponse remplace le texte libre par : accroche, sujets (pictogramme, titre, constat, conséquence, action, zone, fiches, type de produit), suite | Ordre et longueur maîtrisés à la source ; l'app n'a qu'à afficher | Il faut réécrire la consigne de l'agent et le schéma |
| 2. Garder le texte libre et le découper dans l'app | Découpe par phrases ou mots-clés | Pas de changement serveur | Découpe fragile, ordre non garanti, pavé déguisé |
| 3. Uniquement l'accompagnement par l'IA (conversation) | L'IA explique au fil d'un échange | Très guidé | Plus long, plus coûteux ; la personne pressée n'a pas de vue d'ensemble |

Approche 1 retenue. L'accompagnement par l'IA s'appuie dessus : le guide qui écrit annonce chaque sujet (« On passe à votre peau »). Cyrille a dit « vas-y » sans répondre sur l'achat. **Décision de Claude : piste A, lien vers la boutique du partenaire (affiliation).**

## 6. Conception

### 6.1 Réponse de l'agent (serveur)
Le schéma de sortie devient :
```
{ "accroche": "1 phrase, 30 mots au plus, qui répond à l'objectif de la personne",
  "sujets": [ { "pictogramme": <liste fermée>, "titre": "2 à 4 mots", "constat": "≤ 25 mots",
                "consequence": "≤ 25 mots", "action": "≤ 25 mots", "zone": <zone>, "fiches": [id…],
                "produit": <type de produit du catalogue ou null> } ],      // 3 à 5, du plus important au moins important
  "suite": "1 phrase : la prochaine étape proposée" }
```
- La consigne impose l'ordre : l'objectif déclaré d'abord, puis ce qui en découle.
- Pas de jargon sans explication (règle déjà en place).
- Le serveur tronque toute longueur dépassée et garde au plus 5 sujets.
- Le champ `texte` disparaît. L'ancien format reste lu par l'app pendant la transition.

### 6.2 Affichage (app)
- **Bilan :**
  - l'accroche en haut, puis un seul sujet à la fois, en bloc de verre (pictogramme + titre, puis les 3 lignes) ;
  - « Suivant » mène au sujet suivant, et une barre de points en bas montre où on en est (sujet 2 sur 4) ;
  - le dernier écran, « Ce qu'il vous faut », reprend les actions et les produits ;
  - « Tout voir » déplie tous les sujets d'un coup pour qui préfère lire d'une traite.
- **Zone touchée sur le visage :** l'entonnoir actuel garde ses niveaux, au même format de bloc, avec le pictogramme de la zone.
- **Guide :** à chaque changement de sujet, le guide écrit une phrase courte de transition, puis se replie (comportement actuel).
- **Synthèse :** les mêmes blocs, imprimables.

### 6.3 Pictogrammes en points
- Grille carrée de 9 × 9 points, dessinée en canevas, dans un carré fixe de 40 px (24 px dans les listes).
- Dessins abstraits par sujet, liste fermée : cheveux, peau, barbe, yeux, sourcils, lèvres, nez, visage, coupe, couleur, routine-jour, routine-semaine, produits, soleil, sommeil, alimentation.
- Palette sobre sur le fond clair : encre, gris, et une couleur douce par famille (vert d'eau, ocre, bleu-gris, lavande). Pas de rouge.
- Animation :
  - à l'apparition, les points s'allument en balayage (environ 1 s), puis restent fixes ;
  - toutes les 8 à 12 s, un léger passage de 2 à 3 points sur le sujet affiché seulement, rien sur les autres ;
  - aucune animation si la personne a choisi de réduire les mouvements.
- Remplace les symboles en particules actuels.

### 6.4 Achat (piste A)
- Nouveau fichier `partenaires.json` dans le deuxième cerveau (table `offres_partenaires`), exporté vers l'app. Chaque offre contient :
  - partenaire, nom du produit, type de produit du catalogue, prix affiché, lien, date de relevé ;
  - les zones et besoins couverts.
- Une offre n'apparaît que sous un sujet dont l'action utilise ce type de produit.
- Mention « Lien partenaire » sur chaque offre.
- Tant qu'aucun partenaire n'est enregistré, le bloc « Ce qu'il vous faut » montre les types de produits (comme aujourd'hui) avec « Sélection partenaire bientôt disponible ». Aucun produit fictif.
- Les clics vers les partenaires sont comptés sans donnée personnelle (compteur local, puis côté serveur si Cyrille le veut plus tard).

## 7. Décisions prises par Claude (à vérifier)
- Achat : piste A (lien partenaire) faute de réponse.
- Une seule question de couleur par famille de pictogrammes. Grille 9 × 9 et taille 40 px.
- Navigation « Suivant » un sujet à la fois, avec « Tout voir » pour lire d'une traite.

## 8. Laissé au constructeur
Le dessin exact de chaque pictogramme, la durée fine des animations, le découpage des fichiers, la migration de l'ancien format de réponse, les textes de transition du guide.
