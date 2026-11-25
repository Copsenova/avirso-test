import pytest
import keenface as kf


class Rep:
    def __init__(self, code=200, j=None, contenu=b"", texte=""):
        self.status_code, self._j, self.content, self.text = code, j or {}, contenu, texte
    def json(self):
        return self._j


class FauxServeur:
    """Imite l'API : init → PUT → process → get-status (2 fois en cours) → get-3d-model."""
    def __init__(self, init=None, echec=None):
        self.appels, self.etats, self.init, self.echec, self.telechargements = [], ["processing", "processing", "completed"], init, echec, 0
    def post(self, url, headers=None, json=None, timeout=None):
        self.appels.append(("POST", url, json)); assert headers["Authorization"] == "Bearer cle-test"
        if url.endswith("/init"):
            return Rep(j=self.init or {"avatar_id": "av1", "upload_urls": [f"https://depot/{i}" for i in range(json["image_count"])]})
        return Rep(j={"ok": True})
    def put(self, url, headers=None, data=None, timeout=None):
        self.appels.append(("PUT", url, len(data))); return Rep()
    def get(self, url, headers=None, params=None, timeout=None, allow_redirects=True):
        self.appels.append(("GET", url, params))
        if url.endswith("/get-status"):
            e = self.echec or self.etats.pop(0); return Rep(j={"status": e}, texte=e)
        self.telechargements += 1; return Rep(contenu=b"PK\x03\x04zip")


@pytest.fixture(autouse=True)
def cle(monkeypatch):
    monkeypatch.setenv("KEENTOOLS_API_KEY", "cle-test")


PHOTOS = [b"\xff\xd8photo"] * 5


def test_deroule_complet_et_un_seul_telechargement():
    s = FauxServeur(); r = kf.reconstruire(PHOTOS, s, dormir=lambda _: None)
    assert r["id"] == "av1" and r["zip"].startswith(b"PK")
    assert [a[0] for a in s.appels].count("PUT") == 5
    assert s.telechargements == 1
    process = [a for a in s.appels if a[1].endswith("/process")][0]
    assert process[2] == {"focal_length_type": {"focal_length_type": "estimate_common"}}


def test_champs_de_reponse_variables():
    s = FauxServeur(init={"avatar": {"id": "av2"}, "uploads": [{"url": f"https://d/{i}"} for i in range(5)]})
    assert kf.reconstruire(PHOTOS, s, dormir=lambda _: None)["id"] == "av2"


def test_echec_de_reconstruction_signale():
    with pytest.raises(kf.ErreurKeen, match="échouée"):
        kf.reconstruire(PHOTOS, FauxServeur(echec="failed"), dormir=lambda _: None)


def test_nombre_de_photos():
    with pytest.raises(kf.ErreurKeen):
        kf.reconstruire(PHOTOS[:2], FauxServeur(), dormir=lambda _: None)


def test_cle_absente(monkeypatch):
    monkeypatch.delenv("KEENTOOLS_API_KEY")
    with pytest.raises(kf.ErreurKeen, match="secrets Modal"):
        kf.reconstruire(PHOTOS, FauxServeur(), dormir=lambda _: None)


class ServeurLien(FauxServeur):
    """Le téléchargement répond par un JSON contenant un lien vers le ZIP (cas rencontré le 25/11)."""
    def get(self, url, headers=None, params=None, timeout=None, allow_redirects=True):
        if url.startswith("https://stockage/"):
            self.appels.append(("GET", url, headers)); return Rep(contenu=b"PK\x03\x04vrai")
        if url.endswith("/get-3d-model"):
            self.appels.append(("GET", url, params)); self.telechargements += 1
            return Rep(j={"download_url": "https://stockage/tete.zip"}, contenu=b'{"download_url": "https://stockage/tete.zip"}')
        return super().get(url, headers, params, timeout, allow_redirects)


def test_lien_de_telechargement_suivi_sans_retelecharger():
    s = ServeurLien(); r = kf.reconstruire(PHOTOS, s, dormir=lambda _: None)
    assert r["zip"] == b"PK\x03\x04vrai" and s.telechargements == 1
    lien = [a for a in s.appels if a[1].startswith("https://stockage/")][0]
    assert not (lien[2] or {}).get("Authorization")          # la clé ne part pas vers le stockage


def test_reponse_inattendue_gardee_et_id_note():
    class Bizarre(FauxServeur):
        def get(self, url, headers=None, params=None, timeout=None, allow_redirects=True):
            if url.endswith("/get-3d-model"):
                self.telechargements += 1; return Rep(contenu=b"<html>?</html>", j={})
            return super().get(url, headers, params, timeout, allow_redirects)
    notes = []
    with pytest.raises(kf.ErreurKeen) as e:
        kf.reconstruire(PHOTOS, Bizarre(), dormir=lambda _: None, noter=notes.append)
    assert "av1" in str(e.value) and "<html>" in str(e.value)
    assert any("av1" in n for n in notes)
