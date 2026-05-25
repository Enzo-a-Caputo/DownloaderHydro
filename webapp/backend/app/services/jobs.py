"""Fila de jobs com huey (backend SQLite, zero infra externa).

Modelo: cada request de download vira um job persistido. O worker
(`huey_consumer app.services.jobs.huey`) processa em paralelo. O frontend
acompanha pelo endpoint `/api/jobs/{id}`.

Para dev sem worker separado, coloque `HUEY_IMMEDIATE=true` no .env —
a task roda inline na própria request (ruim para downloads longos, mas
útil para smoke-tests).
"""
from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from huey import SqliteHuey

from app import vendor
vendor.install()  # worker não passa pelo main.py — garante que Swagger-ANA-main/ está no sys.path

from app.settings import settings

# Criado fora do consumer: SqliteHuey inicializa conexão preguiçosa.
huey = SqliteHuey(
    name="downloaderhydro",
    filename=str(settings.huey_db_path),
    immediate=settings.huey_immediate,
)

# ---- "catálogo" simples de jobs -----------------------------------------------
# Guardamos metadados em arquivos JSON lado-a-lado do banco huey. Não precisamos
# de um ORM para isso — a fila já é SQLite. Se crescer, migramos.

_JOBS_DIR = settings.huey_db_path.parent / "jobs_meta"
_JOBS_DIR.mkdir(parents=True, exist_ok=True)
_OUTPUTS_DIR = settings.huey_db_path.parent / "outputs"
_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def _meta_path(job_id: str) -> Path:
    return _JOBS_DIR / f"{job_id}.json"


def record_job(job_id: str, data: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    payload = {"created_at": now, "updated_at": now, **data}
    _meta_path(job_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2))


def update_job(job_id: str, **updates: Any) -> None:
    p = _meta_path(job_id)
    if not p.is_file():
        return
    payload = json.loads(p.read_text())
    payload.update(updates)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2))


def read_job(job_id: str) -> dict[str, Any] | None:
    p = _meta_path(job_id)
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def list_jobs(limit: int = 100) -> list[dict[str, Any]]:
    files = sorted(_JOBS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]
    return [json.loads(f.read_text()) for f in files]


# ---- tasks --------------------------------------------------------------------

@huey.task()
def echo_task(job_id: str, message: str) -> str:
    """Task de smoke-test: confirma que a fila está viva."""
    update_job(job_id, status="running")
    try:
        import time
        time.sleep(1)
        update_job(job_id, status="done", result={"echo": message})
        return message
    except Exception as e:
        update_job(job_id, status="failed", error=str(e), traceback=traceback.format_exc())
        raise


@huey.task()
def download_station_task(
    job_id: str,
    kind: str,
    codigo_estacao: str,
    ano_inicial: int,
    ano_final: int,
    tipo_filtro_data: str,
    identificador: str,
    senha: str,
) -> str:
    """Job que baixa a série da ANA e processa em CSV."""
    from app.services import ana
    update_job(job_id, status="running")
    try:
        out_root = _OUTPUTS_DIR / job_id
        json_dir = out_root / "json"
        csv_dir = out_root / "csv"

        ana.download_series(
            kind=kind,
            codigo_estacao=codigo_estacao,
            pasta_saida=json_dir,
            identificador=identificador,
            senha=senha,
            ano_inicial=ano_inicial,
            ano_final=ano_final,
            tipo_filtro_data=tipo_filtro_data,
        )
        try:
            ana.process_series(kind=kind, pasta_json=json_dir, pasta_csv=csv_dir)
        except (NotImplementedError, ValueError):
            # alguns kinds só têm download, sem processamento dedicado — ok
            pass

        update_job(job_id, status="done", output_path=str(out_root))
        return str(out_root)
    except Exception as e:
        update_job(job_id, status="failed", error=str(e), traceback=traceback.format_exc())
        raise
