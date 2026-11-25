# AVIRSO — Visage photoréel et essai de coupes par IA (conception)

Date : 25/11/2026 · Statut : à valider par Cyrille

## 1. Intention

La cliente doit **se reconnaître immédiatement** dans son visage AVIRSO, au niveau de ressemblance des vidéos IA actuelles, puis **essayer des coupes et des couleurs crédibles** sur son propre visage. Sans cela, AVIRSO n'est pas vendable (retour de Cyrille, 25/11).

Constat du 25/11 :
- La tête de démonstration personnalisée (`?tete=mh`) ne ressemble pas assez : crâne du modèle (féminin, étroit), déformation faible (2 à 3 mm en moyenne), photos projetées sur une forme fausse, couleurs faussées par l'éclairage de la démo, coupes génériques.
- L'ancien rendu « tournée » (vraies photos animées par LivePortrait, serveur Modal) ressemblait davantage : la matière est la vraie photo.

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
1. Visage : la vraie personne, de face et de trois-quarts (environ ±40°), net, couleurs fidèles.
2. Essai de coupe : une coupe choisie dans une liste (et une couleur) apparaît sur son visage, de façon réaliste, identité intacte.
3. Les zones cliquables et le maillage lumineux restent disponibles sur ce visage (déjà en place pour la tournée : repères recalculés image par image).
4. Parcours clair : on voit d'abord sa vue de face, puis la rotation ; une coupe montre d'abord la face, puis la rotation.

**Non-objectifs (pour ce lot)**
- Rotation libre à 360° (piste B « tête 3D reconstruite par IA », plus tard, éventuellement à partir des images de ce lot).
- Animation d'expressions, vidéo parlante.

**Anti-objectifs** (échec même si « ça marche »)
- Un visage qui ne ressemble pas, ou qui change d'identité d'une coupe à l'autre.
- Des coupes qui ont l'air de perruques, des couleurs fausses.
- Présenter les images générées comme des photos ou un scan (mention obligatoire : « images générées par un modèle »).
- Garder les photos sur le serveur, ou les mettre dans le dépôt public.

## 3. Contraintes

- Hébergement des calculs : Modal (secret `custom-secret` déjà utilisé pour l'analyse). Déploiement uniquement vers le lien de test (dépôt public Copsenova/avirso-test).
- Licences compatibles avec un usage commercial (code ET poids). Pas de photos de célébrités ni d'images web non licenciées comme références de coupes.
- Consentement : case existante (envoi au serveur) ; les photos sont effacées après calcul (comportement actuel de `fabriquer`).
- Téléphone (iPhone) : l'affichage reste léger (images WebP), le calcul est côté serveur.
- Ne pas modifier `src/scene.ts` sans accord.

## 4. Approches étudiées

| | Principe | Pour | Contre |
|---|---|---|---|
| **A. Photos animées + coupes par IA (retenue)** | Les 3 vraies photos sont la matière ; LivePortrait génère les vues intermédiaires (existant) ; un modèle d'édition d'image change la coupe sur les photos, puis on refait la rotation. | Ressemblance maximale ; coupes photoréalistes ; s'appuie sur l'existant (tournée, zones image par image). | Rotation limitée (≈ ±40°) ; coût serveur par séance et par coupe ; photos envoyées au serveur. |
| B. Tête 3D reconstruite par IA (OMG-Avatar, OMEGA-Avatar, MeshLAM…) | Une tête complète (gaussiennes ou maillage) à partir d'une photo. | Rotation libre. | Arrière et côtés inventés ; code et licence commerciale incertains ; changer de coupe exige de toute façon A. |
| C. Améliorer la tête MakeHuman | Meilleure forme, ombres retirées. | Déjà en place. | Plafond « jeu vidéo » : n'atteindra pas le niveau visé. Écartée. |

Choix de Cyrille (25/11) : **A**. B reste une option ultérieure.

## 5. Conception retenue

### 5.1 Visage (tournée de qualité)
- Le parcours par défaut de l'essai devient la **tournée** (images générées à partir des 3 photos), à la place de la tête de démonstration personnalisée. `?tete=mh` reste accessible pour comparaison, sans être proposé.
- Qualité : réglages serveur revus pour la netteté (WebP de meilleure qualité, taille d'image adaptée à l'écran Retina, contrôle de la couleur : pas de dérive de teinte entre la photo et les images générées).
- Ordre d'affichage : la vue de face (vraie photo recadrée) s'affiche tout de suite ; la rotation arrive quand elle est prête.

### 5.2 Essai de coupe par édition d'image
- Modèle : **Qwen-Image-Edit-2511** (Apache 2.0, poids publics, conçu pour garder l'identité dans les retouches de portrait), servi sur Modal (GPU grande mémoire). Accélération possible par une version à pas réduits (Lightning) si la qualité tient.
- Entrée : la photo de face + une consigne texte construite par AVIRSO (coupe + longueur + texture + couleur, et « garder le visage, la peau, la barbe, l'éclairage et le fond identiques »).
- Cohérence entre les vues : la photo de face est retouchée d'abord ; les deux trois-quarts sont retouchés ensuite avec la face retouchée comme deuxième image de référence (« même coupe que l'image 2 »). Puis la tournée est recalculée sur les 3 photos retouchées.
- Catalogue : une liste de coupes écrite par AVIRSO (consignes texte, pas d'images de référence) : court, dégradé, bouclé court, afro, tresses plaquées, locks, mi-long, long lisse, long bouclé… et un nuancier de couleurs (le nuancier existant de l'app). Les coupes conseillées par l'analyse sont proposées en premier.
- Affichage : rangée « Essayer une coupe » (déjà conçue) ; la face retouchée s'affiche d'abord (objectif < 30 s), puis la rotation retouchée (objectif < 90 s). « Ta coupe » revient à l'original instantanément. Chaque résultat est gardé pendant la séance (pas de recalcul si on revient sur une coupe).
- Mention : « Coupe générée par un modèle sur votre photo : un aperçu, pas une promesse de résultat. »

### 5.3 Zones et maillage lumineux
- Inchangés : repères MediaPipe recalculés sur chaque image de la tournée (code existant `tournee3d.ts`, `voileImage.ts`). Ils s'appliquent aussi aux images retouchées.

### 5.4 Confidentialité et coûts
- Les photos et les images générées ne sont pas conservées sur le serveur (dossier temporaire supprimé, comme `fabriquer`).
- Coût estimé à mesurer pendant le prototype (temps GPU par coupe et par tournée), puis à afficher à Cyrille avant toute ouverture au public.

## 6. Étape 0 : prototype de validation (avant tout développement)

Sur les photos de Cyrille, en local au serveur, sans toucher à l'app :
1. Retoucher la photo de face avec 4 coupes (dégradé, afro, tresses, long) et 2 couleurs.
2. Retoucher les trois-quarts avec la méthode de cohérence ci-dessus.
3. Recalculer une tournée sur un jeu retouché.
4. Mesurer temps et coût ; montrer les images à Cyrille.

Critère pour continuer : Cyrille se reconnaît sur chaque image et juge les coupes crédibles. Sinon : essayer une autre méthode (autre modèle d'édition, ou transfert de coiffure dédié) avant de développer.

## 7. Décisions prises par Claude (à vérifier)
- Sans accord d'envoi au serveur : on garde le relief local actuel (vraies photos en relief), sans essai de coupe.
- Démarrage du modèle de coupe : réveillé pendant la séance photo (comme la tournée aujourd'hui), pour éviter l'attente du chargement (poids de plusieurs dizaines de Go).
- `?tete=mh` et la bibliothèque de coupes 3D restent dans le code, non proposés par défaut.

## 8. Laissé au constructeur

Choix du GPU, nombre de pas, résolution, format des échanges avec l'app, découpage des fonctions Modal, écriture exacte des consignes, ordre de chargement, gestion des erreurs et des délais.
