# AVIRSO — mise en scène du portrait : la tête seule, éclairée comme sur un plateau, sur un fond qui se fond dans la page.
# Entrées : l'image de la tête (générée), la découpe de la personne et du vêtement. Aucun modèle ici : uniquement du calcul d'image.
#   - le vêtement devient une silhouette sombre, sans couleur : on ne voit plus ce que la personne porte ;
#   - la lumière est celle d'un portrait de studio : douce, un peu plus forte d'un côté, avec un léger liseré de l'autre ;
#   - l'étalonnage reste discret : un peu de contraste, ombres légèrement froides, peau légèrement chaude ;
#   - la sortie est la personne SEULE, avec sa transparence : c'est l'application qui pose le fond de studio derrière.
#     Pour l'animation de contrôle (vidéo), `sur_fond` pose la même personne sur un fond de studio clair.
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

    def composer(self, A, alpha, habit, cx, col):
        """A : image (bleu-vert-rouge). alpha : personne (0 à 1). habit : vêtement (0 à 1). cx : milieu du cou. col : hauteur du col.
        Renvoie la personne éclairée, avec sa transparence (4 canaux : bleu, vert, rouge, alpha)."""
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
        img = lum + (img - lum) * 0.96
        img = np.clip(img, 0, 1); img = img * img * (3 - 2 * img) * 0.30 + img * 0.70
        img = img * 1.06 + (1 - lum) ** 2 * np.array([[[0.030, 0.008, -0.010]]], np.float32) + lum ** 2 * np.array([[[-0.012, 0.004, 0.018]]], np.float32)
        # 4. lumière : principale d'un côté (gauche de l'image), l'autre côté dans l'ombre ; le cou s'éteint vers le bas
        u = np.clip((fx - cx) / 0.20, -1, 1) * 0.5 + 0.5
        cle = 1.08 - 0.26 * (u * u * (3 - 2 * u))
        v = np.clip((fy - (col - 0.07)) / 0.12, 0, 1)
        cle = cle * (1 - 0.30 * v * v)
        img = img * cle[..., None]
        # le vêtement devient une silhouette : presque noir, sans couleur ; on ne voit plus ce que la personne porte
        gris = (0.114 * img[..., 0] + 0.587 * img[..., 1] + 0.299 * img[..., 2])[..., None]
        silhouette = np.clip(gris, 0, 1) * 0.04 + np.array([[[0.030, 0.018, 0.014]]], np.float32)      # noir à peine bleuté : une silhouette, plus un vêtement
        img = img * (1 - ombre[..., None]) + silhouette * ombre[..., None]
        # 5. contre-jour : un liseré clair et froid sur le bord du côté sombre
        bande = np.clip(a - cv2.GaussianBlur(cv2.erode(a, self.k_lis), (0, 0), 7 * sg), 0, 1)
        # contre-jour bleu des deux côtés (plus fort du côté sombre), qui dessine aussi les épaules
        cote = np.clip(np.abs(fx - cx) / 0.10, 0, 1) * np.where(fx > cx, 1.0, 0.55)
        liser = bande * cote * (1 - 0.35 * v)
        img += liser[..., None] * np.array([[[0.60, 0.30, 0.14]]], np.float32)
        # 6. sortie : la personne seule, avec sa transparence (bord adouci)
        a3 = cv2.GaussianBlur(a, (0, 0), 1.2 * sg)
        return np.dstack([np.clip(img, 0, 1) * 255.0, a3 * 255.0]).astype(np.uint8)

    def sur_fond(self, bgra, cx=0.5, cy=0.40):
        """Pour la vidéo de contrôle : la personne sur un fond de studio (clair derrière la tête, sombre vers les bords et le bas)."""
        fx, fy = self.fx, self.fy
        r = np.sqrt(((fx - cx) / 0.62) ** 2 + ((fy - cy) / 0.62) ** 2)
        k = np.exp(-(r ** 2) * 1.5)[..., None]
        fond = np.array([[PAGE]], np.float32) * (1 - k) + np.array([[[178, 160, 140]]], np.float32) * k
        a = bgra[..., 3:4].astype(np.float32) / 255
        out = a * bgra[..., :3].astype(np.float32) + (1 - a) * fond + self.alea.normal(0, 1.2, (self.T, self.T, 1)).astype(np.float32)
        return np.clip(out, 0, 255).astype(np.uint8)
