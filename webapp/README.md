# DownloaderHydro — WebApp

Webapp local que integra:
- **delineator** (mghydro.com/watersheds) → delineação de bacias a partir de clique no mapa
- **Swagger-ANA** → inventário e download de dados de estações da ANA dentro da bacia

Os projetos originais (`delineator-main/`, `Swagger-ANA-main/`) continuam intactos
fora de `webapp/` — servem de backup e fonte de verdade para a lógica científica.

## Arquitetura

```
DownloaderHydro/
├── delineator-main/         # intacto, importado como biblioteca
├── Swagger-ANA-main/        # intacto, importado como biblioteca
└── webapp/
    ├── backend/             # FastAPI + huey (SQLite)
    ├── frontend/            # Vite + TypeScript + Leaflet
    └── scripts/             # preparação de dados
```

## Fluxo

1. Usuário clica no mapa → `POST /api/delineate` → backend retorna GeoJSON da bacia
2. Frontend envia a bacia → `POST /api/stations` → retorna códigos PLU/FLU dentro
3. Usuário clica "baixar" numa estação → `POST /api/downloads` → job enfileirado
4. Worker huey processa em segundo plano → usuário acompanha `/api/jobs/{id}` e baixa `.zip`

## Subir em dev (3 processos)

```bash
# 1) backend
cd webapp/backend && uvicorn app.main:app --reload

# 2) worker da fila
cd webapp/backend && huey_consumer app.services.jobs.huey -w 2

# 3) frontend
cd webapp/frontend && npm install && npm run dev
# abrir http://localhost:5173
```

Para desenvolvimento sem worker, `HUEY_IMMEDIATE=true` no `.env` — tasks rodam
inline no processo da API. Bom para debug, ruim para downloads longos.

## Próximos passos (ordem recomendada)

1. **Fase de dados** — seguir `scripts/prepare_merit_sa.md` para baixar MERIT-Hydro
   da América do Sul. Sem isso o `/api/delineate` devolve 503.
2. **Inventário ANA** — `scripts/build_ana_inventory.py` (stub). Implementar e
   gerar `storage/estacoes_ana.gpkg` quando for o momento.
3. **Smoke test** — subir backend com `HUEY_IMMEDIATE=true`, rodar
   `curl -X POST localhost:8000/api/jobs/echo?message=oi` para validar a fila.
4. **Primeira bacia real** — clicar em uma localização dentro de uma das
   megabacias pré-carregadas e verificar o resultado no mapa.

## Pontos de extensão

- **PostGIS**: substituir `ShapefileStore` por `PostGISStore` em
  `app/services/catchments/` — resto do código não muda.
- **Mundo inteiro**: adicionar mais códigos em `PRELOAD_BASINS`, baixar os
  dados correspondentes. Nenhuma mudança de código.
- **Empacotamento nativo**: adicionar `pywebview` em cima do FastAPI.
