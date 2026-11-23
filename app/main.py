from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router as api_router
from app.core.config import get_settings

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="NexusCore AI — Enterprise Supply Chain & Risk Intelligence",
    description=(
        "Platform Intelijen Rantai Pasok Otonom berbasis Hybrid GraphRAG (NetworkX + Qdrant RRF), "
        "XGBoost Predictive ML, Monte Carlo Simulation, dan Hierarchical Multi-Agent Swarm."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_war_room_ui():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        {
            "message": "NexusCore AI Backend API aktif. Buka /docs untuk Swagger UI.",
            "docs_url": "/docs",
            "health_url": "/api/health",
        }
    )
