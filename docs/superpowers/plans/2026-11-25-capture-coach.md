# Capture guidée en direct (« coach ») — plan

> Exécution en ligne (superpowers:executing-plans). Design validé par Cyrille le 25/11 (« Oui »).

**But :** dès que la caméra s'allume, une seule consigne à la fois s'affiche à côté du visage (police à points), le cadre suit le visage ; les photos se prennent seules (flash + « C'est bon, j'en ai une »), la caméra ne s'arrête jamais ; fin : « J'ai tout ce qu'il me faut ».

**Architecture :** on transforme `direct()` dans `lot1/web/src/essai/essai.ts` (MediaPipe déjà en place). Étapes : face → menton haut → menton bas → trois-quarts gauche → profil → trois-quarts droit → profil de l'autre côté. Vues requises par la tête 3D inchangées (face, deux trois-quarts, profil facultatif). Réserve silencieuse : meilleures images par case angle×inclinaison (40 au plus), en mémoire, non envoyées (reconstruction future).

## Décisions
- Voix : NON (retirée le 24/11 à la demande de Cyrille, « trop robotique ») ; guidage écrit seulement.
- Étapes facultatives (menton, profils) : « Passer cet angle » après 10 s sans succès ; vues requises : jamais passées.
- Écran d'accord raccourci ; « Commencer » lance la caméra en direct ; « une par une » reste en lien secondaire.

## Tâches
1. Test `parcours/capture_coach.mjs` (caméra simulée) : cadre qui suit, consigne à côté du visage, pas de vignettes ni jauge, flashs, « C'est bon », passage des angles manquants, fin « J'ai tout ce qu'il me faut », réserve ≥ 8 images, écran de vérification ; aucune erreur.
2. Implémentation `direct()` + styles `essai.css`/`clair.css` ; accord raccourci.
3. Non-régression, publication, vérification en ligne.
