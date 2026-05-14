from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.database import SessionLocal, init_db
from app.routers.health import router as health_router
from app.routers.api_admin import router as api_admin_router
from app.routers.admin_ui import router as admin_ui_router
from app.services.bootstrap import seed_initial_data

APP_VERSION = "0.3.4-partner-products"

app = FastAPI(
    title="HUB ASTORIE APP",
    version=APP_VERSION,
    description="Admin Core pro postupný převod HUBu z Google Apps Scriptu do Pythonu.",
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
        "status": "v0.3.4 Partner Products Admin is loaded",
    }


@app.get("/admin-test")
def admin_test():
    return {
        "ok": True,
        "message": "Admin test route exists. If /admin fails, template routing is the issue.",
        "version": APP_VERSION,
    }


# API + UI routers
app.include_router(health_router)
app.include_router(api_admin_router)
app.include_router(admin_ui_router)
