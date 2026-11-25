# Visagiste (lot 2) — plan d'implémentation

> Exécution : superpowers:executing-plans (en ligne). Choix validé par Cyrille le 25/11 : option 1 (l'IA choisit dans des listes fermées).

**But :** à partir des photos, l'IA recommande coupe, couleur, barbe, monture, couleurs de vêtements et outils, chacun choisi dans une liste fermée et sourcé ; l'application l'affiche dans un onglet « Visagiste », un sujet à la fois, avec « Essayer sur ma photo » pour coupe, couleur et barbe.

**Architecture :** listes fermées dans `serveur-tete/visagiste.py` (montures, couleurs de vêtements, outils) + catalogue des styles existant (coupes, couleurs, barbes) ; le conseiller reçoit ces listes et renvoie un bloc `visagiste` contraint par schéma (enums) ; `nettoyer_visagiste` revérifie et résout les noms. Côté app, `parcoursVue` affiche le bloc comme un parcours ; démo : une vraie sortie de l'IA sur le visage fictif, présentée comme exemple.

**Spec :** messages de Cyrille du 25/11 (lot 2) et proposition validée (option 1) ; bibliothèque : lot 10 `sources_lot10_visagiste.py` (19 fiches).

## Contraintes
- Aucun produit, prix ou marque inventés ; toute recommandation vient d'une liste fermée.
- Couleurs de vêtements : présentées comme « pratique de métier ».
- Photos jamais dans le dépôt public ; démo = visage fictif.

## Tâches
1. Bibliothèque : lot 10 ajouté, exporté vers l'app et le serveur. (fait)
2. Serveur : `visagiste.py` (listes, schéma, `nettoyer_visagiste`) ; tests `test_visagiste.py` ; branchement dans `agents.py` (consigne, schéma, sortie `visagiste`) ; déploiement ; appel réel sur visage fictif.
3. App : type `Visagiste` dans `essai/serveur.ts`, passage par `contenuPerso` ; onglets « Bilan | Visagiste » dans `#ens` ; parcours visagiste (6 sujets, pictogrammes coupe/couleur/barbe/yeux/produits/cheveux) ; fin « Ce qu'il vous faut » (outils + bientôt disponible) ; « Essayer sur ma photo » qui ouvre la feuille des styles présélectionnée (absent en démo) ; démo `visagisteExemple.json`. Test `parcours/visagiste.mjs`.
4. Publication, vérification en ligne, relecture.

## À surveiller
- IA qui choisit une coupe incompatible avec la texture → filtrer par `textures` du catalogue.
- Personne sans barbe → « aucune » permis.
- Réponse trop longue → budget conseiller relevé.
