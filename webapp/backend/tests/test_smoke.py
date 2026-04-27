"""Testes mínimos que rodam sem dados MERIT nem credenciais ANA."""
from fastapi.testclient import TestClient


def test_health():
    from app.main import app
    with TestClient(app) as client:
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_echo_job():
    from app.main import app
    from app.services import jobs as jobs_module

    # Em CI/dev, forçar execução inline
    jobs_module.huey.immediate = True

    with TestClient(app) as client:
        r = client.post("/api/jobs/echo", params={"message": "oi"})
        assert r.status_code == 200
        job_id = r.json()["job_id"]

        r2 = client.get(f"/api/jobs/{job_id}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "done"
