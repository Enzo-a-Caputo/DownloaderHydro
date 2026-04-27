from __future__ import annotations

import traceback

from fastapi import APIRouter, HTTPException, Request

from app.schemas import DelineateRequest, DelineateResponse, Precision
from app.services.delineate import delineate_point

router = APIRouter(tags=["delineate"])


@router.post("/delineate", response_model=DelineateResponse)
async def post_delineate(req: DelineateRequest, request: Request) -> DelineateResponse:
    store = request.app.state.catchment_store
    try:
        result = delineate_point(
            req.lat, req.lng, store,
            precision=req.precision.value if isinstance(req.precision, Precision) else req.precision,
            simplify=req.simplify,
            fill=req.fill,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Dados MERIT ausentes: {e}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Falha na delineação: {type(e).__name__}: {e}")

    return DelineateResponse(
        watershed=result.watershed_geojson,
        rivers=result.rivers_geojson,
        area_km2=result.area_km2,
        lat_snap=result.lat_snap,
        lng_snap=result.lng_snap,
        snap_dist_m=result.snap_dist_m,
        basin_pfaf2=result.basin_pfaf2,
        mode=result.mode,
    )
