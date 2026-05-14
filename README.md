# HUB ASTORIE APP – v0.2

První nahratelný základ pro GitHub + Render + Neon.

## Obsah
- FastAPI backend
- připojení na Neon PostgreSQL přes `DATABASE_URL`
- automatické vytvoření základních tabulek při startu
- `/` úvodní stránka
- `/health` kontrola běhu
- `/api/admin/summary` kontrola počtů v databázi
- `/docs` API dokumentace

## Render
Build Command:
`pip install -r requirements.txt`

Start Command:
`uvicorn app.main:app --host 0.0.0.0 --port 10000`


## Hotfix v0.2.1

Přidán `runtime.txt` s Pythonem 3.12.8.
Důvod: Render použil Python 3.14, který způsobil chybu kompatibility se SQLAlchemy typováním.


## Hotfix v0.2.2

Modely byly převedeny ze SQLAlchemy `Mapped[...]` syntaxe na klasickou `Column(...)` syntaxi.
Důvod: Render stále spouštěl Python 3.14 a původní typování se na této kombinaci lámalo.
