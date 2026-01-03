from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from app.database import create_db_and_tables
from app.routers import tasks, admin
from app.config import get_settings

# Configure logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "mimi_app.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    logger.info("Starting Mimi.Today application...")
    create_db_and_tables()
    logger.info("Database initialized")
    yield
    # Shutdown: cleanup if needed
    logger.info("Shutting down Mimi.Today application...")


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


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon."""
    favicon_path = Path(__file__).parent.parent / "static" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return FileResponse(status_code=204)  # No content



