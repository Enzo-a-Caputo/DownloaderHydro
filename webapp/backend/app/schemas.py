from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Precision(str, Enum):
    high = "high"
    low = "low"
    auto = "auto"


class DelineateRequest(BaseModel):
    lat: float = Field(ge=-60, le=85)
    lng: float = Field(ge=-180, le=180)
    precision: Precision = Precision.auto
    simplify: bool = False
    fill: bool = True


class DelineateResponse(BaseModel):
    watershed: dict[str, Any]       # GeoJSON Feature (Polygon/MultiPolygon)
    rivers: dict[str, Any] | None   # GeoJSON FeatureCollection
    area_km2: float
    lat_snap: float
    lng_snap: float
    snap_dist_m: float
    basin_pfaf2: int
    mode: Literal["high", "low"]


class StationsRequest(BaseModel):
    watershed: dict[str, Any]       # GeoJSON Feature/FeatureCollection/Geometry


class Station(BaseModel):
    codigo: str
    tipo: Literal["Pluviométrica", "Fluviométrica"]
    lat: float
    lng: float
    nome: str | None = None


class StationsResponse(BaseModel):
    pluviometricas: list[Station]
    fluviometricas: list[Station]


class DownloadKind(str, Enum):
    chuva = "chuva"
    cota = "cota"
    vazao = "vazao"
    curva_descarga = "curva_descarga"
    perfil_transversal = "perfil_transversal"
    qa = "qa"
    resumo_descarga = "resumo_descarga"
    sedimentos = "sedimentos"
    dados = "dados"
    telemetrica_detalhada = "telemetrica_detalhada"
    telemetrica_adotada = "telemetrica_adotada"


class DownloadRequest(BaseModel):
    codigo_estacao: str
    kind: DownloadKind
    ano_inicial: int = 1900
    ano_final: int = 2025
    tipo_filtro_data: Literal["DATA_LEITURA", "DATA_ULTIMA_ATUALIZACAO"] = "DATA_LEITURA"
    # se não informado, usa credenciais do .env
    identificador: str | None = None
    senha: str | None = None


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


class Job(BaseModel):
    id: str
    kind: str
    status: JobStatus
    codigo_estacao: str | None = None
    progress: float = 0.0
    created_at: datetime
    updated_at: datetime
    output_path: str | None = None
    error: str | None = None
