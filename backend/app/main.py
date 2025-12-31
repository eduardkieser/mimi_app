from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from pathlib import Path

from app.database import create_db_and_tables
from app.routers import tasks, admin
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    create_db_and_tables()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# CORS for Flutter web / dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Local network only, so this is fine
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(tasks.router)
app.include_router(admin.router)

# Static files for HTMX frontend
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Templates for HTMX frontend
templates_path = Path(__file__).parent.parent / "templates"
if templates_path.exists():
    templates = Jinja2Templates(directory=templates_path)

    @app.get("/")
    async def mimi_page(request: Request):
        """Mimi's task view (HTMX)."""
        return templates.TemplateResponse("mimi.html", {"request": request})

    @app.get("/admin")
    async def admin_page(request: Request):
        """Ilse's admin view (HTMX)."""
        return templates.TemplateResponse("admin.html", {"request": request})

    @app.get("/theme-test")
    async def theme_test_page(request: Request):
        """Theme testing/debugging page."""
        return templates.TemplateResponse("theme_test.html", {"request": request})


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}



