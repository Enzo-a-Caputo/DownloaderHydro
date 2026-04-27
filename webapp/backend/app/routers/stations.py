from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import Station, StationsRequest, StationsResponse
from app.services import ana

router = APIRouter(tags=["stations"])


@router.post("/stations", response_model=StationsResponse)
async def post_stations(req: StationsRequest) -> StationsResponse:
    try:
        result = ana.clip_stations_by_basin(req.watershed)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao cruzar estações: {e}")

    return StationsResponse(
        pluviometricas=[Station(**s) for s in result["pluviometricas"]],
        fluviometricas=[Station(**s) for s in result["fluviometricas"]],
    )
