from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.routers.health import router as health_router
from app.routers.admin import router as admin_router
from app.services.bootstrap import seed_initial_data

app = FastAPI(title="HUB ASTORIE APP", version="0.2.4-clean")


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()


app.include_router(health_router)
app.include_router(admin_router)


@app.get("/", response_class=HTMLResponse)
def index():
    return f'''
    <!doctype html>
    <html lang="cs">
      <head>
        <meta charset="utf-8">
        <title>{settings.app_name}</title>
        <style>
          body {{ margin:0; font-family:Arial,sans-serif; background:#f3f6f7; color:#102a2f; }}
          .wrap {{ max-width:980px; margin:48px auto; padding:0 20px; }}
          .card {{ background:white; border-radius:24px; padding:34px; box-shadow:0 22px 60px rgba(0,0,0,.12); border-top:8px solid {settings.brand_primary}; }}
          h1 {{ margin:0; color:{settings.brand_primary}; font-size:38px; }}
          .badge {{ display:inline-block; margin-top:14px; background:{settings.brand_secondary}; color:white; padding:8px 14px; border-radius:999px; font-weight:700; }}
          a {{ color:{settings.brand_primary}; font-weight:700; }}
          .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; margin-top:26px; }}
          .box {{ border:1px solid #dbe5e8; border-radius:16px; padding:16px; background:#f8fbfc; }}
        </style>
      </head>
      <body>
        <div class="wrap">
          <div class="card">
            <h1>{settings.app_name}</h1>
            <div class="badge">v0.2.4 clean – spuštěno</div>
            <p>Backend HUBu běží na Renderu a je napojený na Neon PostgreSQL.</p>
            <div class="grid">
              <div class="box"><b>Health</b><br><a href="/health">/health</a></div>
              <div class="box"><b>Admin summary</b><br><a href="/api/admin/summary">/api/admin/summary</a></div>
              <div class="box"><b>API docs</b><br><a href="/docs">/docs</a></div>
            </div>
          </div>
        </div>
      </body>
    </html>
    '''
