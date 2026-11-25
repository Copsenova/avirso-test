# Diagnostic KeenFace : appels de CONSULTATION seulement (jamais get-3d-model, qui est facturé).
import modal
app = modal.App("avirso-keenface-diag")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests==2.32.3")


@app.function(image=image, secrets=[modal.Secret.from_name("keentools")], timeout=120)
def consulter(chemins: list[str]) -> list[str]:
    import os, requests
    h = {"Authorization": f"Bearer {os.environ['KEENTOOLS_API_KEY'].strip()}"}
    out = []
    for c in chemins:
        assert "get-3d-model" not in c
        try:
            r = requests.get("https://api.keenface.ai" + c, headers=h, timeout=30)
            out.append(f"{c} -> {r.status_code} {r.headers.get('content-type','')} {r.text[:700]}")
        except Exception as e:
            out.append(f"{c} -> erreur {e}")
    return out


@app.local_entrypoint()
def main(chemins: str):
    for l in consulter.remote(chemins.split(",")):
        print(l)
