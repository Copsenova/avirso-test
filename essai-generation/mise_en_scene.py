# AVIRSO — mise en scène du portrait : la tête seule, éclairée comme sur un plateau, sur un fond qui se fond dans la page.
# Entrées : l'image de la tête (générée), la découpe de la personne et du vêtement. Aucun modèle ici : uniquement du calcul d'image.
#   - le vêtement devient une silhouette sombre, sans couleur : on ne voit plus ce que la personne porte ;
#   - une lumière principale vient d'un côté, l'autre côté tombe dans l'ombre, avec un liseré de contre-jour ;
#   - l'étalonnage est celui d'une image de cinéma : contraste, ombres froides, hautes lumières chaudes ;
#   - le fond est celui de la page (même couleur aux bords), avec une lueur derrière la tête.
import numpy as np, cv2

PAGE = (19, 13, 11)          # couleur de fond de l'application (#0b0d13), en bleu-vert-rouge


class Scene:
    def __init__(self, taille, graine=7):
        self.T = T = taille
        self.fy, self.fx = np.mgrid[0:T, 0:T].astype(np.float32) / T
        self.alea = np.random.default_rng(graine)
        self.k_bord = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, ((int(round(11 * T / 1024)) | 1,) * 2))
        self.k_hab = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, ((int(round(9 * T / 1024)) | 1,) * 2))
        self.k_lis = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, ((int(round(17 * T / 1024)) | 1,) * 2))

    def fond(self, cx, cy):
        """Fond de plateau : la couleur de la page aux bords, une lueur froide derrière la tête, un faisceau venant du haut à gauche."""
        r = np.sqrt(((self.fx - cx) / 0.46) ** 2 + ((self.fy - cy) / 0.50) ** 2)
        lueur = np.exp(-(r ** 2) * 1.6)[..., None]
        faisceau = (np.clip(1 - (self.fx * 0.8 + self.fy * 0.9), 0, 1) ** 2)[..., None] * np.exp(-(r ** 2) * 0.5)[..., None]
        f = np.array([[PAGE]], np.float32) + lueur * np.array([[[30, 22, 17]]], np.float32) + faisceau * np.array([[[22, 24, 30]]], np.float32)
        return f

    def composer(self, A, alpha, habit, cx, col):
        """A : image (bleu-vert-rouge). alpha : personne (0 à 1). habit : vêtement (0 à 1). cx : milieu du cou. col : hauteur du col."""
        T, fx, fy = self.T, self.fx, self.fy
        alpha = alpha.reshape(T, T).astype(np.float32); habit = habit.reshape(T, T).astype(np.float32)
        sg = T / 1024
        # 1. on garde toute la personne ; le buste ne disparaît pas, il passe dans l'ombre (étape 4) et s'efface tout en bas de l'image
        ombre = np.clip(cv2.GaussianBlur(cv2.dilate(habit, self.k_hab), (0, 0), 7 * sg) * 1.5, 0, 1)
        bas = np.clip(1 - (fy - 0.86) / 0.12, 0, 1); bas = bas * bas * (3 - 2 * bas)
        a = alpha * bas
        # 2. couleur du bord prise à l'intérieur (aucune trace du décor d'origine)
        dedans = cv2.erode(a, self.k_bord)
        Af = A.astype(np.float32)
        inter = cv2.GaussianBlur(Af * dedans[..., None], (0, 0), 5 * sg) / (cv2.GaussianBlur(dedans, (0, 0), 5 * sg)[..., None] + 1e-3)
        m = cv2.GaussianBlur(dedans, (0, 0), 2 * sg)[..., None]
        img = (m * Af + (1 - m) * inter) / 255.0
        # 3. étalonnage : un peu moins de couleur, plus de contraste, ombres froides et hautes lumières chaudes
        lum = (0.114 * img[..., 0] + 0.587 * img[..., 1] + 0.299 * img[..., 2])[..., None]
        img = lum + (img - lum) * 0.90
        img = np.clip(img, 0, 1); img = img * img * (3 - 2 * img) * 0.55 + img * 0.45
        img += (1 - lum) ** 2 * np.array([[[0.020, 0.006, -0.012]]], np.float32) + lum ** 2 * np.array([[[-0.020, 0.004, 0.026]]], np.float32)
        # 4. lumière : principale d'un côté (gauche de l'image), l'autre côté dans l'ombre ; le cou s'éteint vers le bas
        u = np.clip((fx - cx) / 0.20, -1, 1) * 0.5 + 0.5
        cle = 1.16 - 0.64 * (u * u * (3 - 2 * u))
        v = np.clip((fy - (col - 0.07)) / 0.12, 0, 1)
        cle = cle * (1 - 0.45 * v * v)
        img = img * cle[..., None]
        # le vêtement devient une silhouette : presque noir, sans couleur ; on ne voit plus ce que la personne porte
        gris = (0.114 * img[..., 0] + 0.587 * img[..., 1] + 0.299 * img[..., 2])[..., None]
        silhouette = np.clip(gris, 0, 1) * 0.10 + np.array([[[0.050, 0.036, 0.030]]], np.float32)
        img = img * (1 - ombre[..., None]) + silhouette * ombre[..., None]
        # 5. contre-jour : un liseré clair et froid sur le bord du côté sombre
        bande = np.clip(a - cv2.GaussianBlur(cv2.erode(a, self.k_lis), (0, 0), 7 * sg), 0, 1)
        liser = bande * np.clip((fx - cx) / 0.10, 0, 1) * (1 - 0.6 * v)
        img += liser[..., None] * np.array([[[0.50, 0.40, 0.33]]], np.float32)
        # 6. pose sur le fond, puis même grain léger sur le tout
        a3 = cv2.GaussianBlur(a, (0, 0), 1.2 * sg)[..., None]
        cy = col - 0.30
        sortie = a3 * np.clip(img, 0, 1) * 255.0 + (1 - a3) * self.fond(cx, cy)
        sortie += self.alea.normal(0, 1.3, (T, T, 1)).astype(np.float32)
        return np.clip(sortie, 0, 255).astype(np.uint8)
