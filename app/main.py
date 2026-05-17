from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.database import SessionLocal, init_db
from app.routers.health import router as health_router
from app.routers.api_admin import router as api_admin_router
from app.routers.admin_ui import router as admin_ui_router
from app.services.bootstrap import seed_initial_data

APP_VERSION = "1.3.3-emergency-rollback-safe"

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
        "status": "v1.3.3 emergency rollback: stable adviser routes are forced via main.py",
    }


@app.get("/admin-test")
def admin_test():
    return {
        "ok": True,
        "message": "Admin test route exists. If /admin fails, template routing is the issue.",
        "version": APP_VERSION,
    }




# -------------------------------------------------------------------
# v1.2.6 Main Route Bridge Safe
# -------------------------------------------------------------------
# Nouzová stabilizace: pevné aplikační aliasy jsou registrované přímo
# v main.py před include_router(...), takže mají přednost před starými
# nebo neúplně zaregistrovanými routerovými variantami.
# DB, import ani sekce Partneři se nemění.

@app.get("/api/release-1-2-6/status")
def release_126_status():
    return {
        "ok": True,
        "version": APP_VERSION,
        "message": "Main route bridge je aktivní. Opravené veřejné HUB URL jsou registrované přímo v main.py.",
        "safe": True,
        "db_changed": False,
        "partners_changed": False,
        "routes_bridged": {
            "/hub/calculators": "/hub/calculators-old-v083",
            "/hub/forms": "/hub/forms-old-v083",
            "/hub/stats": "/hub/stats-old-v083",
            "/hub/help": "/hub/help-old-v083",
            "/hub/new-tip": "/hub/new-tip-old-v085",
        },
    }


@app.get("/hub/calculators")
def hub_calculators_main_bridge():
    return RedirectResponse(url="/hub/calculators-old-v083", status_code=302)


@app.get("/hub/forms")
def hub_forms_main_bridge():
    return RedirectResponse(url="/hub/forms-old-v083", status_code=302)


@app.get("/hub/stats")
def hub_stats_main_bridge():
    return RedirectResponse(url="/hub/stats-old-v083", status_code=302)


@app.get("/hub/help")
def hub_help_main_bridge():
    return RedirectResponse(url="/hub/help-old-v083", status_code=302)


@app.get("/hub/new-tip")
def hub_new_tip_main_bridge():
    return RedirectResponse(url="/hub/new-tip-old-v085", status_code=302)



# -------------------------------------------------------------------
# v1.3.3 Emergency Rollback Safe
# -------------------------------------------------------------------
# Důvod: po verzi 1.3.2 hlásily poradenské sekce mimo Partnery interní chybu.
# Tato verze neexperimentuje s novým UI layerem. Vrací stabilní přímé
# aliasy v main.py před include_router(...), aby se rozbité nové routy
# vůbec nespustily. DB, importy ani Partneři se nemění.

@app.get("/api/release-1-3-3/status")
def release_133_status():
    return {
        "ok": True,
        "version": APP_VERSION,
        "message": "Nouzový rollback: poradenské sekce jsou pevně přemostěné na poslední stabilní šablony. DB ani Partneři se nemění.",
        "safe": True,
        "db_changed": False,
        "partners_changed": False,
        "forced_routes": {
            "/hub/new-tip": "/hub/new-tip-old-v085",
            "/hub/my-tips": "/hub/my-tips-old-v085",
            "/hub/calculators": "/hub/calculators-old-v083",
            "/hub/forms": "/hub/forms-old-v083",
            "/hub/stats": "/hub/stats-old-v083",
            "/hub/help": "/hub/help-old-v083",
            "/hub/contacts": "/hub/contacts-old-v083"
        }
    }

@app.get("/hub/my-tips")
def hub_my_tips_main_bridge():
    return RedirectResponse(url="/hub/my-tips-old-v085", status_code=302)

@app.get("/hub/contacts")
def hub_contacts_main_bridge():
    return RedirectResponse(url="/hub/contacts-old-v083", status_code=302)

# API + UI routers
app.include_router(health_router)
app.include_router(api_admin_router)
app.include_router(admin_ui_router)
