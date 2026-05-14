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
