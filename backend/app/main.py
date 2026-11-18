"""FastAPI application entry point"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import auth, projects, series_bible, characters, locations, episodes, scenes, dialogues, prompts, assets, google_accounts, flow_bridge, story_engine, settings as settings_api, shots


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Micro Drama Production SaaS API",
    lifespan=lifespan,
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Malformed input (e.g. a non-UUID path/body value) is a 400, not a 500.

    Routers call uuid.UUID(...) directly on path params; without this
    handler a malformed UUID bubbled up as an unhandled 500 (audit F-H3).
    """
    return JSONResponse(status_code=400, content={"detail": f"Invalid value: {exc}"})

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(series_bible.router, prefix="/api")
app.include_router(characters.router, prefix="/api")
app.include_router(locations.router, prefix="/api")
app.include_router(episodes.router, prefix="/api")
app.include_router(scenes.router, prefix="/api")
app.include_router(dialogues.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(google_accounts.router, prefix="/api")
app.include_router(flow_bridge.router, prefix="/api")
app.include_router(story_engine.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(shots.router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }