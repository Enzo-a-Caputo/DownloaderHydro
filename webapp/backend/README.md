# DownloaderHydro — Backend

API FastAPI que expõe:
- Delineação de bacias (envolvendo `delineator-main/`)
- Interseção bacia × estações ANA (envolvendo `Swagger-ANA-main/`)
- Fila de downloads em segundo plano (huey + SQLite)

## Setup

```bash
cd webapp/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # editar com seus paths
```

## Executar (dev)

Três processos:

```bash
# 1) API
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 2) Worker da fila de downloads
huey_consumer app.services.jobs.huey -w 2

# 3) Frontend (em webapp/frontend/)
npm run dev
```

Ou, para desenvolvimento rápido, set `HUEY_IMMEDIATE=true` no `.env` — a fila executa inline no próprio processo da API (sem worker separado, sem persistência).

## Estrutura

```
app/
├── main.py              FastAPI + lifespan (carrega GDFs no boot)
├── settings.py          pydantic-settings
├── vendor.py            adiciona delineator-main/ e Swagger-ANA-main/ ao sys.path
├── schemas.py           modelos Pydantic
├── routers/             endpoints HTTP
└── services/
    ├── catchments/      CatchmentStore (abstração de fonte de dados)
    ├── delineate.py     função pura delineate_point()
    ├── ana.py           wrap Swagger-ANA
    └── jobs.py          huey + tasks de download
```

## Dependência de dados externos

Esse backend **não roda** sem dados MERIT baixados. Ver `../scripts/prepare_merit_sa.md` para o checklist.
