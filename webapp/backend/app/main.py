from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import vendor
vendor.install()           # precisa vir antes de qualquer import do delineator/Swagger-ANA
vendor.configure_delineator()  # injeta nossos paths nos globals do config.py do delineator

from app.routers import delineate, stations, downloads, jobs
from app.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante que o configure rodou (ex.: testes que importam main fora do uvicorn)
    vendor.configure_delineator()

    # Pré-carregar GDFs das bacias configuradas em PRELOAD_BASINS
    from app.services.catchments.shapefile import ShapefileStore
    store = ShapefileStore()
    app.state.catchment_store = store
    for basin in settings.preload_basins_list:
        try:
            store.get_megabasins()  # carrega uma única vez
            store.get_catchments(basin, high_res=True)
            store.get_rivers(basin)
        except FileNotFoundError as e:
            # dado ausente ≠ erro fatal: servidor sobe e avisa
            print(f"[warn] bacia {basin} não pôde ser pré-carregada: {e}")
    yield
    # sem teardown por enquanto


app = FastAPI(
    title="DownloaderHydro API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(delineate.router, prefix="/api")
app.include_router(stations.router, prefix="/api")
app.include_router(downloads.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


# ------------------------------------------------------------------
# Static frontend (opcional): se existir webapp/frontend/dist, monta /
# ------------------------------------------------------------------
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
else:
    @app.get("/")
    async def root() -> JSONResponse:
        return JSONResponse(
            {
                "message": "Backend no ar. Rode o frontend com `npm run dev` em webapp/frontend/.",
                "docs": "/docs",
                "health": "/api/health",
            }
        )
