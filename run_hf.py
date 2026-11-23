import os
from pathlib import Path

# Nonaktifkan Node SSR Proxy Gradio agar trafik '/' dan API langsung ditangani FastAPI
os.environ["GRADIO_SSR_MODE"] = "false"
os.environ["NO_PROXY"] = "localhost,127.0.0.1,0.0.0.0"
os.environ["no_proxy"] = "localhost,127.0.0.1,0.0.0.0"

import gradio as gr
import gradio.routes
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import router as api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.vector_store import get_qdrant_client, init_qdrant_collections

try:
    from app.api.routes import limiter
except ImportError:
    limiter = Limiter(key_func=get_remote_address)

settings = get_settings()
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

try:
    import spaces

    @spaces.GPU
    def gpu_health_ping(text: str) -> str:
        return f"NexusCore AI Ready: {text}"

except ImportError:

    def gpu_health_ping(text: str) -> str:
        return f"NexusCore AI Ready: {text}"


# 1. Inisialisasi tabel PostgreSQL / SQLite & koleksi Qdrant Cloud tanpa mereset data live
try:
    init_db()
except Exception as exc:
    print(f"[Startup Warning] init_db dilewati: {exc}")

try:
    init_qdrant_collections()
    qdrant_client = get_qdrant_client()
    col_info = qdrant_client.get_collection(settings.qdrant_docs_collection)
    if (col_info.points_count or 0) == 0:
        from app.rag.indexer import index_all_corporate_docs

        index_all_corporate_docs()
except Exception as exc:
    print(f"[Startup Warning] Inisialisasi Qdrant dilewati (fallback aktif): {exc}")


# 2. Sisipkan FastAPI routes, Swagger UI (/docs), & Light-First Web UI ke server internal Gradio
_orig_create_app = gradio.routes.App.create_app


def _custom_create_app(blocks, *args, **kwargs):
    gradio_app = _orig_create_app(blocks, *args, **kwargs)

    # Ganti rute '/', '/docs', dan '/openapi.json' bawaan Gradio dengan milik NexusCore AI
    gradio_app.router.routes = [
        r
        for r in gradio_app.router.routes
        if getattr(r, "path", None) not in {"/", "/docs", "/openapi.json"}
    ]

    gradio_app.state.limiter = limiter
    gradio_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    gradio_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    gradio_app.include_router(api_router)

    if FRONTEND_DIR.exists():
        gradio_app.mount(
            "/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static"
        )

    # Dukung GET dan HEAD agar startup healthcheck Gradio selalu menerima HTTP 200
    @gradio_app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    def serve_frontend():
        return FileResponse(FRONTEND_DIR / "index.html")

    @gradio_app.get("/openapi.json", include_in_schema=False)
    def custom_openapi():
        if gradio_app.openapi_schema:
            return gradio_app.openapi_schema
        api_routes = [
            r for r in gradio_app.routes if getattr(r, "path", "").startswith("/api")
        ]
        openapi_schema = get_openapi(
            title="NexusCore AI — Enterprise Supply Chain & Risk Intelligence API",
            version="1.0.0",
            description=(
                "Platform Intelijen Rantai Pasok Otonom berbasis Hybrid GraphRAG (NetworkX + Qdrant RRF), "
                "XGBoost Predictive ML, Monte Carlo Simulation, dan Hierarchical Multi-Agent Swarm."
            ),
            routes=api_routes,
        )
        gradio_app.openapi_schema = openapi_schema
        return openapi_schema

    @gradio_app.get("/docs", include_in_schema=False)
    def custom_swagger_ui():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="NexusCore AI — Swagger API Docs",
        )

    return gradio_app


gradio.routes.App.create_app = _custom_create_app

with gr.Blocks(title="NexusCore AI") as demo:
    gr.Markdown("# NexusCore AI")
    with gr.Row(visible=False):
        ping_input = gr.Textbox(value="OK")
        ping_output = gr.Textbox()
        ping_btn = gr.Button("Ping")
        ping_btn.click(fn=gpu_health_ping, inputs=ping_input, outputs=ping_output)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", ssr_mode=False)
