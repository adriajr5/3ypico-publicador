#!/usr/bin/env python3
"""Publica en Instagram el/los carrusel(es) que tocan hoy (hora de Madrid).
Variables: IG_TOKEN, IG_USER_ID, SLOT (1 o 2), DRY_RUN=1 para probar sin publicar."""
import json, os, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

API = "https://graph.instagram.com/v21.0"
BASE_FOTOS = "https://adriajr5.github.io/3ypico-publicador/"
TOKEN = os.environ.get("IG_TOKEN", "")
UID = os.environ.get("IG_USER_ID", "")
DRY = os.environ.get("DRY_RUN") == "1"
SLOT = int(os.environ.get("SLOT") or 1)
HOY = os.environ.get("FECHA") or datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d")

def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    req = urllib.request.Request(url if method == "POST" else url + "?" + data.decode(),
                                 data=data if method == "POST" else None, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Error de Instagram ({e.code}): {e.read().decode()}")

def esperar(cid):
    for _ in range(30):
        st = call("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            sys.exit(f"El contenedor {cid} fallo: {st}")
        time.sleep(5)
    sys.exit(f"Tiempo agotado esperando {cid}")

def comprobar(url):
    req = urllib.request.Request(url, method="HEAD")
    try:
        urllib.request.urlopen(req, timeout=30).close()
    except Exception as e:
        sys.exit(f"La foto no es accesible todavia: {url} ({e})")

posts = json.load(open("posts.json", encoding="utf-8"))
hecho = json.load(open("publicados.json")) if os.path.exists("publicados.json") else []
clave = lambda p: f"{p['fecha']}#{p['slot']}"
toca = [p for p in posts if p["fecha"] == HOY and p["slot"] == SLOT and clave(p) not in hecho]
if not toca:
    print(f"{HOY} slot {SLOT}: nada que publicar.")
    sys.exit(0)

for p in toca:
    urls = [BASE_FOTOS + p["carpeta"] + "/" + f for f in p["fotos"]]
    print("Publicando:", clave(p), p["carpeta"], f"({len(urls)} fotos)")
    if DRY:
        print(p["texto"]); continue
    for u in urls:
        comprobar(u)
    hijos = []
    for u in urls:
        c = call("POST", f"{UID}/media", image_url=u, is_carousel_item="true")["id"]
        hijos.append(c)
    for c in hijos:
        esperar(c)
    car = call("POST", f"{UID}/media", media_type="CAROUSEL", children=",".join(hijos), caption=p["texto"])["id"]
    esperar(car)
    pub = call("POST", f"{UID}/media_publish", creation_id=car)["id"]
    print("Publicado, id", pub)
    hecho.append(clave(p))
    json.dump(hecho, open("publicados.json", "w"), indent=1)
