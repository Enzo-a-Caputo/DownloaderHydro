from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.schemas import StationsRequest, StationsResponse, Station
from app.services import ana

router = APIRouter(tags=["stations"])


@router.get("/inventory")
async def get_inventory() -> JSONResponse:
    """Retorna todas as estações do inventário como GeoJSON FeatureCollection."""
    try:
        fc = ana.get_inventory_geojson()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler inventário: {e}")
    return JSONResponse(fc)


@router.post("/stations", response_model=StationsResponse)
async def post_stations(req: StationsRequest) -> StationsResponse:
    try:
        result = ana.clip_stations_by_basin(req.watershed)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao cruzar estações: {e}")

    def _to_station(d: dict) -> Station:
        return Station(
            codigo=d.get("CODIGO", ""),
            tipo=d.get("TIPOESTACA", ""),
            lat=d["lat"],
            lng=d["lng"],
            nome=d.get("NOME") or d.get("Estacao_Nome") or None,
            props=d,
        )

    return StationsResponse(
        pluviometricas=[_to_station(s) for s in result["pluviometricas"]],
        fluviometricas=[_to_station(s) for s in result["fluviometricas"]],
    )
