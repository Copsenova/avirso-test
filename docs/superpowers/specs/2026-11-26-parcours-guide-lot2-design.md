# Parcours guidé — lot 2 : l'analyse réelle au format chapitres

Date : 26/11/2026 · Statut : à valider par Cyrille
Complète `2026-11-26-parcours-guide-design.md` (spec validée). Le lot 1 (démo) est en ligne.

## Pourquoi

Le parcours guidé n'existe que sur le visage fictif. Une personne qui a payé et fait ses photos retombe sur l'ancien affichage (onglets Bilan / Visagiste, zones), celui qui « perd » le client. Le lot 2 lui donne le même rendez-vous visagiste, écrit pour son visage.

## Ce qui existe aujourd'hui (serveur Modal `serveur-tete`)

1. **L'analyste** (IA, avec les 3 photos) décrit : texture et type de boucle, longueur, barbe, carnation, sous-ton, yeux, sourcils, forme du visage, fiabilité, limites.
2. **Le conseiller** (IA, sans les photos) reçoit cette description, les attentes de la personne et les 185 fiches sourcées. Il rédige l'accroche et 3 à 5 sujets, et choisit coupe, couleur, barbe, monture, couleurs de vêtements et outils **dans des listes fermées**. Le serveur revérifie tout : identifiants connus, coupes compatibles avec la texture, fiches existantes.

## Approches

1. **Le conseiller écrit aussi les chapitres, dans le même appel** (retenue). Il a déjà la description, les fiches et les listes. On ajoute un bloc « chapitres » à sa réponse structurée, et le serveur le revérifie comme le reste. Coût : la réponse est plus longue, donc l'attente aussi (à mesurer).
2. **Un troisième appel dédié aux chapitres.** Plus ciblé, mais il ajoute un appel entier, donc encore plus d'attente et de coût. Écartée tant que la 1 donne un bon texte.
3. **Fabriquer les chapitres dans le navigateur à partir des sujets existants.** Pas d'IA en plus, mais rien pour remplir « ce que ça veut dire », les trois propositions ou la routine : on aurait des chapitres creux. Écartée.

## Ce qui est construit

**Serveur**
- Le conseiller rend `ouverture` (3 phrases : forme du visage, cheveux, peau et sous-ton) et `chapitres`, au tutoiement, au format du lot 1 : vu (2 à 4 constats + étiquettes), sens, objectif, trois propositions + une chose à éviter, routine (3 ou 4 gestes), produits.
- Les propositions viennent des listes fermées quand il y en a une :
  - Cheveux : coupes du catalogue, filtrées par texture, avec essai « coupe » ;
  - Barbe : styles du catalogue ;
  - Lunettes : montures ;
  - Couleurs : couleurs de vêtements ;
  - Peau, Regard : texte libre, appuyé sur les fiches choisies.
- Les produits sont pris dans la liste fermée des types de produits : jamais de marque. Les exemples réels viennent de la bibliothèque côté app, comme dans la démo.
- Le serveur revérifie : identifiants connus, noms remplacés par ceux des listes, coupe incompatible avec la texture écartée, longueurs bornées. Un chapitre incomplet est retiré, on ne montre pas de chapitre vide.
- **Barbe** : le chapitre n'existe que si une barbe est visible sur les photos, ou si la personne a choisi l'objectif « barbe ». Sinon il est retiré, côté serveur et côté affichage.
- Les sujets actuels restent produits pour l'instant (anciennes versions de l'app, repli).

**App**
- Analyse réelle avec chapitres → le parcours guidé, le même que la démo : ton visage 3D, toucher une zone ouvre son chapitre, « Ma fiche ».
- Analyse sans chapitres (ancienne analyse, ou réponse incomplète) → l'affichage actuel, inchangé.
- Tutoiement autour du guide, comme dans la démo.
- Protection des données qui viennent du serveur : tout texte échappé, identifiants d'essai et liens filtrés (deux points relevés à la relecture du lot 1).

## Vérification

- Tests du serveur avec de fausses réponses de l'IA : chapitre incomplet retiré, identifiant inventé écarté, coupe incompatible écartée, barbe retirée sans barbe visible, rien d'injecté.
- Tests de l'app avec une analyse réelle simulée : guide affiché, barbe absente ou présente selon le profil, repli sur l'ancien affichage si pas de chapitres.
- **Un vrai essai** sur le serveur Modal avec tes photos (accord donné le 25/11), pour juger le texte et mesurer l'attente. Coût : un appel d'IA et quelques minutes de serveur sans carte graphique.

## Hors de ce lot

- **« Corrige-moi »** (corriger un constat, puis relancer le conseiller) : petit lot à part, juste après celui-ci, une fois le texte réel jugé.
- Les essais coupe, couleur et monture dans l'écran 3 : lot 3.

## Mes choix (à corriger si besoin)

- Approche 1 (un seul appel).
- Barbe : barbe visible ou objectif « barbe ». L'IA ne devine pas le genre, c'est une règle de l'analyste.
- Tutoiement aussi dans l'espace personnel, autour du guide.
- « Corrige-moi » reporté juste après ce lot.
