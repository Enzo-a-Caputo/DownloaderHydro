from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.services import jobs

router = APIRouter(tags=["jobs"])


@router.get("/jobs")
async def get_jobs(limit: int = 100) -> list[dict]:
    return jobs.list_jobs(limit=limit)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    meta = jobs.read_job(job_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return meta


@router.get("/jobs/{job_id}/download")
async def download_job_output(job_id: str) -> StreamingResponse:
    meta = jobs.read_job(job_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if meta.get("status") != "done":
        raise HTTPException(status_code=409, detail=f"Job não finalizado (status={meta.get('status')})")

    out = Path(meta["output_path"])
    if not out.is_dir():
        raise HTTPException(status_code=410, detail="Saída do job não está mais disponível")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in out.rglob("*"):
            if p.is_file():
                zf.write(p, arcname=p.relative_to(out))
    buf.seek(0)

    filename = f"{meta.get('codigo_estacao', 'job')}_{meta['kind']}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/jobs/echo")
async def post_echo(message: str = "hello") -> dict:
    """Smoke-test da fila: cria um job que só ecoa uma mensagem."""
    job_id = uuid.uuid4().hex
    jobs.record_job(job_id, {"id": job_id, "kind": "echo", "status": "queued"})
    jobs.echo_task(job_id, message)
    return {"job_id": job_id}
