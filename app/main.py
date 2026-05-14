from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.database import SessionLocal, init_db
from app.routers.health import router as health_router
from app.routers.api_admin import router as api_admin_router
from app.routers.admin_ui import router as admin_ui_router
from app.services.bootstrap import seed_initial_data

app = FastAPI(
    title="HUB ASTORIE APP",
    version="0.3.0-admin-core",
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


app.include_router(health_router)
app.include_router(api_admin_router)
app.include_router(admin_ui_router)
