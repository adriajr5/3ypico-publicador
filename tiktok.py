#!/usr/bin/env python3
"""TikTok: sube a la bandeja de borradores del dueno el carrusel que toca hoy.
  python3 tiktok.py auth <codigo>   -> canjea el codigo de autorizacion y guarda los tokens cifrados
  python3 tiktok.py post            -> sube los borradores de hoy (SLOT=1|2, FECHA=AAAA-MM-DD opcional, DRY_RUN=1)"""
import json, os, subprocess, sys, urllib.request, urllib.parse, urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

KEY = os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
SEC = os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
REDIRECT = "https://adriajr5.github.io/3ypico-publicador/callback.html"
BASE = "https://adriajr5.github.io/3ypico-publicador/"
ENC = "tiktok_token.enc"
DRY = os.environ.get("DRY_RUN") == "1"

def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Error de TikTok ({e.code}): {e.read().decode()[:600]}")

def token_post(**p):
    p.update(client_key=KEY, client_secret=SEC)
    return http("https://open.tiktokapis.com/v2/oauth/token/", urllib.parse.urlencode(p).encode(),
                {"Content-Type": "application/x-www-form-urlencoded"})

def guardar(t):
    r = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:TIKTOK_STATE_KEY", "-out", ENC],
                       input=json.dumps(t).encode(), capture_output=True)
    if r.returncode: sys.exit("No se pudo cifrar: " + r.stderr.decode())

def cargar():
    if not os.path.exists(ENC):
        sys.exit("Falta autorizar TikTok (ejecuta el workflow 'Autorizar TikTok').")
    r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:TIKTOK_STATE_KEY", "-in", ENC], capture_output=True)
    if r.returncode: sys.exit("No se pudo descifrar: revisa el secreto TIKTOK_STATE_KEY.")
    return json.loads(r.stdout)

if not KEY or not SEC:
    sys.exit("Faltan los secretos TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET.")
if not os.environ.get("TIKTOK_STATE_KEY"):
    sys.exit("Falta el secreto TIKTOK_STATE_KEY.")

modo = sys.argv[1] if len(sys.argv) > 1 else "post"

if modo == "auth":
    res = token_post(grant_type="authorization_code", code=sys.argv[2].strip(), redirect_uri=REDIRECT)
    if "refresh_token" not in res:
        sys.exit("Respuesta inesperada de TikTok: " + json.dumps({k: v for k, v in res.items() if "token" not in k}))
    guardar({"refresh_token": res["refresh_token"], "open_id": res.get("open_id")})
    print("Autorizacion guardada. Permisos:", res.get("scope"))
    sys.exit(0)

slot = int(os.environ.get("SLOT") or 1)
hoy = os.environ.get("FECHA") or datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d")
posts = json.load(open("posts_tiktok.json", encoding="utf-8"))
hecho = json.load(open("publicados_tiktok.json")) if os.path.exists("publicados_tiktok.json") else []
clave = lambda p: f"{p['fecha']}#{p['slot']}"
toca = [p for p in posts if p["fecha"] == hoy and p["slot"] == slot and clave(p) not in hecho]
if not toca:
    print(f"{hoy} slot {slot}: nada que subir."); sys.exit(0)

if DRY:
    for p in toca: print("Subiria:", clave(p), p["carpeta"], len(p["fotos"]), "fotos\n" + p["texto"])
    sys.exit(0)

t = cargar()
res = token_post(grant_type="refresh_token", refresh_token=t["refresh_token"])
if "access_token" not in res:
    sys.exit("No se pudo renovar el acceso: " + json.dumps({k: v for k, v in res.items() if "token" not in k}))
t["refresh_token"] = res.get("refresh_token", t["refresh_token"])
guardar(t)
acc = res["access_token"]

for p in toca:
    urls = [BASE + p["carpeta"] + "/" + f for f in p["fotos"]]
    lineas = p["texto"].strip().split("\n")
    body = {"post_info": {"title": lineas[0][:90], "description": p["texto"][:4000]},
            "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": 0, "photo_images": urls},
            "post_mode": "MEDIA_UPLOAD", "media_type": "PHOTO"}
    r = http("https://open.tiktokapis.com/v2/post/publish/content/init/", json.dumps(body).encode(),
             {"Authorization": "Bearer " + acc, "Content-Type": "application/json; charset=UTF-8"})
    err = r.get("error", {})
    if err.get("code") != "ok":
        sys.exit("TikTok rechazo el borrador: " + json.dumps(err))
    print("Borrador enviado:", clave(p), p["carpeta"], "publish_id", r.get("data", {}).get("publish_id"))
    hecho.append(clave(p))
    json.dump(hecho, open("publicados_tiktok.json", "w"), indent=1)
