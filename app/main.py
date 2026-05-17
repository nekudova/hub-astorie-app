from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.database import SessionLocal, init_db
from app.routers.health import router as health_router
from app.routers.api_admin import router as api_admin_router
from app.routers.admin_ui import router as admin_ui_router
from app.services.bootstrap import seed_initial_data

APP_VERSION = "1.3.2-stable-core-route-restore-safe"

app = FastAPI(
    title="HUB ASTORIE APP",
    version=APP_VERSION,
    description="HUB ASTORIE – postupný převod původního TIP Hubu z Google Apps Scriptu do Pythonu.",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.state.templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()


@app.head("/")
def head_root():
    return JSONResponse(status_code=200, content={})


@app.get("/version")
def version():
    return {
        "ok": True,
        "version": APP_VERSION,
        "admin_route_expected": "/admin",
        "status": "v1.3.2 stable core + restored hub routes is loaded",
    }


@app.get("/admin-test")
def admin_test():
    return {
        "ok": True,
        "message": "Admin test route exists. If /admin fails, template routing is the issue.",
        "version": APP_VERSION,
    }




# -------------------------------------------------------------------
# v1.3.2 Stable Core Route Restore Safe
# -------------------------------------------------------------------
# Stabilizační verze postavená na posledním funkčním jádru v1.2.6.
# Důležité: zde už NEJSOU nouzové redirecty pro /hub/calculators,
# /hub/new-tip, /hub/forms, /hub/stats a /hub/help.
# Přímé routy obsluhuje admin_ui.py, aby se načítala aktuální šablona
# včetně fulltextu Sazebníku a aby nebyly odříznuté sekce TIPů.
# DB, importy ani Partneři se nemění.

@app.get("/api/release-1-3-2/status")
def release_132_status():
    return {
        "ok": True,
        "version": APP_VERSION,
        "message": "Obnoveno stabilní jádro HUBu; odstraněny přepisující redirecty; vráceny TIP routy a fulltext sazebníku.",
        "safe": True,
        "db_changed": False,
        "partners_changed": False,
        "routes_restored": [
            "/hub/new-tip",
            "/hub/my-tips",
            "/hub/tips/{tip_id}",
            "/hub/specialist-tips",
            "/hub/specialist-tips/{tip_id}",
            "/hub/calculators",
            "/hub/forms",
            "/hub/stats",
            "/hub/help",
            "/hub/contacts",
            "/hub/partners"
        ]
    }


# API + UI routers
app.include_router(health_router)
app.include_router(api_admin_router)
app.include_router(admin_ui_router)
