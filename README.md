# 3ypico publicador
Publica automaticamente en Instagram los carruseles de `posts.json` (2 un dia, 1 al siguiente).
- Fotos en `fotos/` (servidas por GitHub Pages).
- `publicar.py` lo ejecuta GitHub Actions cada dia (ver `.github/workflows/publicar.yml`).
- `publicados.json` registra lo ya publicado para no repetir.
- Secretos necesarios: `IG_TOKEN`, `IG_USER_ID`.
