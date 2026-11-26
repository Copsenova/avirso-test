# Parcours visagiste guidé — conception

Date : 26/11/2026 · Statut : à valider par Cyrille
Maquettes validées : https://claude.ai/artifact/5ZqTDBXuV73eF1aTgwoymQ (chapitre Cheveux, 6 écrans)

## Pourquoi

Cyrille, en testant la démo : « je ne sais pas où aller, il y a trop d'informations, ce n'est pas assez guidé ». Il veut ressentir **un visagiste qui lui parle** : ce qu'il voit, ce que ça veut dire, ce qui lui irait, et la solution concrète (coupe, routine, produits), « comme au coiffeur ».

Défauts constatés dans la démo actuelle (26/11) :
- quatre portes d'entrée concurrentes : onglets Bilan / Visagiste, 12 zones anatomiques, Plan ;
- rangement par anatomie et non par question du client (« Cheveux » = 4 observations de coiffage, sans type de cheveux, routine, produits ni essai de coupe) ;
- profil ignoré : l'exemple visagiste propose une barbe au mannequin féminin ;
- ton de rapport, tout affiché d'un coup.

## Objectifs

- Un seul chemin guidé, chapitre après chapitre, bouton « Suivant », avec possibilité de sauter un chapitre.
- Chaque chapitre suit **toujours les mêmes 4 écrans** : Ce que je vois → Ce que ça veut dire → Ce que je te conseille → Ta routine.
- À la fin, **une fiche** (à montrer au coiffeur, routine, liste de produits).
- Le ton : une personne qui parle, phrases courtes, « pourquoi » relié aux traits de la personne.
- **Rien perdre du design** (demande explicite) : fond dégradé ardoise, verre clair, polices Doto et Geist Mono, pictogrammes abstraits existants (`apercu/symboles.ts`) et leurs sous-pictogrammes, rendu futuriste et « touche d'IA ».

## Non-objectifs

- La nouvelle tête 3D (essais de reconstruction) : hors de ce chantier ; on garde l'afficheur et le mannequin actuels.
- Les liens d'affiliation : toujours « Sélection partenaire bientôt disponible ».
- Refaire la capture photo.

## Anti-objectifs (ce serait un échec même si ça marche)

- Un conseil qui ne correspond pas au profil (barbe pour une femme, coupe incompatible avec la texture).
- Plus d'un bouton principal par écran, ou plus de ~4 idées par écran.
- Des produits, marques ou chiffres inventés.
- Perdre un élément graphique validé.

## Chapitres

Ordre : **Cheveux, Peau, Barbe, Regard et sourcils, Lunettes, Couleurs** (vêtements).
- **Barbe** n'apparaît que si le profil le justifie (homme ou personne avec pilosité faciale détectée). Pas de barbe = chapitre absent, et aucun outil de barbe proposé ailleurs.
- Un chapitre sans contenu fiable n'apparaît pas (pas de chapitre vide).

Écran d'ouverture « Voilà ce que je vois » : trois phrases au plus (forme du visage, type de cheveux, sous-ton de peau), la liste des chapitres, « On commence par… ».

## Les 4 écrans d'un chapitre

1. **Ce que je vois** : la zone surlignée sur le visage 3D, 2 à 4 constats, des étiquettes (ex. « Type 4A », « Dense », « Pointes sèches »), lien « Corrige-moi » (le client rectifie un constat erroné).
2. **Ce que ça veut dire** : 2 ou 3 phrases d'explication, puis l'**objectif en une phrase**.
3. **Ce que je te conseille** : trois propositions (premier choix, choix sûr, choix audacieux), chacune avec son pourquoi, plus **une chose à éviter** ; bouton « Essayer sur moi » quand un essai existe (coupe, couleur, barbe, monture).
4. **Ta routine** : 3 ou 4 gestes numérotés (avec fréquence), puis les **types de produits**, chacun ouvrant ses exemples réels de la bibliothèque (Open Beauty Facts, outils sourcés).

Le visage 3D reste visible en haut des écrans 1 et 3 ; toucher une zone du visage ouvre directement le chapitre correspondant (raccourci, pas menu principal).

## Le design

- Fond, verre, polices, couleurs : `ui/clair.css` tel quel.
- Pictogrammes : `symboles.ts` (cheveux, peau, barbe, yeux, sourcils, lèvres, nez, visage, coupe, couleur, routine, produits, soleil, sommeil, lunettes, vêtements, outils…) en tête de chaque chapitre et de chaque geste ; les petits sous-pictogrammes abstraits par sujet sont conservés.
- Touche IA : texte qui s'écrit progressivement à l'ouverture d'un écran (déjà en place, coupé si « moins d'animations »), balayage discret sur la zone du visage 3D, indicateur d'étapes en points.
- Le bip, la capture coach et le reste du parcours ne changent pas.

## Données

- **Démo (visage fictif)** : un exemple complet et cohérent, réécrit pour le mannequin féminin (cheveux, peau, regard, lunettes, couleurs ; pas de barbe), au format chapitres.
- **Analyse réelle** : le serveur (agents) produit le même format chapitres ; les choix restent pris dans les listes fermées existantes (coupes filtrées par texture, montures, couleurs, outils) et dans la bibliothèque (185 fiches, exemples produits).
- Format d'un chapitre : `{ id, picto, vu: [{texte, etiquette?}], sens: [texte], objectif, conseils: {premier, sur, audacieux: {id, nom, pourquoi, essai?}, eviter}, routine: [{geste, frequence, picto?}], produits: [{type, exemples?}] }`.
- Le profil (genre déclaré ou détecté, pilosité, texture) filtre les chapitres et les choix côté serveur **et** côté affichage.

## Approches envisagées

1. **Réorganiser l'écran actuel** (onglets, zones) en gardant ses blocs : rapide, mais garde les quatre portes d'entrée qui perdent le client. Écartée.
2. **Parcours guidé par chapitres** au-dessus des données existantes, avec un format chapitre commun démo / analyse réelle : choisie par Cyrille le 26/11 (« Guider », maquettes validées).
3. **Conversation libre avec l'IA (chat)** : très « humain », mais lent, imprévisible et difficile à rendre fiable. Écartée pour l'instant.

## Ce qui est décidé par Cyrille

- Parcours guidé (26/11, « Guider »).
- Organisation des maquettes validée « complètement » ; tout le design et les pictogrammes existants conservés ; futuriste, moderne, touche d'IA.

## Mes choix (à corriger si besoin)

- Tutoiement dans tout le parcours (les maquettes tutoient ; le site actuel vouvoie par endroits).
- Ordre des chapitres ci-dessus.
- Les anciens onglets Bilan / Visagiste et la liste des 12 zones disparaissent comme porte d'entrée ; le Plan devient la Fiche finale.
- Mise en œuvre par lots : 1) démo statique complète au nouveau format, 2) serveur au format chapitres, 3) essais (coupe, couleur…) branchés dans l'écran 3.

## Laissé au constructeur

- Le découpage exact des composants, l'animation d'écriture, la façon de mémoriser l'avancement.
