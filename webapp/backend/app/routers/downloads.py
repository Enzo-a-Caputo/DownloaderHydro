from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request

from app.schemas import DownloadRequest
from app.services import jobs
from app.settings import settings

router = APIRouter(tags=["downloads"])


@router.post("/downloads")
async def post_download(req: DownloadRequest, request: Request) -> dict:
    # Prioridade: sessão > corpo do request > .env
    identificador = request.session.get("identificador") or req.identificador or settings.ana_identificador
    senha         = request.session.get("senha")         or req.senha         or settings.ana_senha

    if not identificador or not senha:
        raise HTTPException(
            status_code=401,
            detail="Credenciais ANA ausentes. Faça login primeiro.",
        )

    job_id = uuid.uuid4().hex
    jobs.record_job(job_id, {
        "id": job_id,
        "kind": req.kind.value,
        "codigo_estacao": req.codigo_estacao,
        "status": "queued",
        "ano_inicial": req.ano_inicial,
        "ano_final": req.ano_final,
    })

    jobs.download_station_task(
        job_id,
        req.kind.value,
        req.codigo_estacao,
        req.ano_inicial,
        req.ano_final,
        req.tipo_filtro_data,
        identificador,
        senha,
    )

    return {"job_id": job_id, "status": "queued"}
