"""Camada fina sobre o Swagger-ANA.

Importa os módulos do `Swagger-ANA-main/` (via vendor) e expõe funções de alto
nível que os routers e o worker huey podem usar.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from app.settings import settings

# Colunas canônicas que o backend usa; mapeamos a partir dos nomes reais do GPKG
_COL_CODIGO = "CODIGO"
_COL_TIPO   = "TIPOESTACA"

# Valores aceitos para tipo (com e sem acento — o notebook normaliza, mas defensivo)
_PLUV = {"Pluviométrica", "Pluviometrica"}
_FLUV = {"Fluviométrica", "Fluviometrica"}


def _load_inventory() -> gpd.GeoDataFrame:
    if not settings.ana_inventory_path.is_file():
        raise FileNotFoundError(
            f"Inventário ANA não encontrado: {settings.ana_inventory_path}. "
            "Gere com Inventario_ANA.ipynb e copie para esta pasta."
        )
    return gpd.read_file(settings.ana_inventory_path).to_crs("EPSG:4326")


def _row_to_dict(row) -> dict:
    """Converte uma linha do GeoDataFrame em dict serializável (sem geometry)."""
    import math
    d = {}
    for k, v in row.items():
        if k == "geometry":
            continue
        if v is None or (hasattr(v, '__class__') and v.__class__.__name__ in ('NAType', 'NaTType')):
            d[k] = None
            continue
        try:
            val = v.item() if hasattr(v, 'item') else v
            # NaN / Inf não são JSON-válidos — converte para None
            d[k] = None if (isinstance(val, float) and not math.isfinite(val)) else val
        except Exception:
            d[k] = str(v)
    return d


# ── inventário completo ────────────────────────────────────────────────────────

# Campos enviados ao frontend para o mapa global (mínimo para renderização e filtros).
# Detalhes completos ficam no GPKG e são retornados pelo /api/stations (clip por bacia).
_INVENTORY_FIELDS = ("CODIGO", "TIPOESTACA", "NOME", "Operando", "Municipio_Nome", "UF_Estacao")


def get_inventory_geojson() -> dict:
    """Retorna todas as estações como GeoJSON compacto (só campos essenciais).

    Servir todos os 60+ campos para 37k estações produziria >100 MB — inviável
    no browser. Os detalhes completos ficam no GPKG e são retornados pelo
    /api/stations (clip por bacia) quando o usuário delineia.
    """
    inv = _load_inventory()
    features = []
    for _, row in inv.iterrows():
        geom = row.geometry
        if geom is None:
            continue
        props = {}
        for k in _INVENTORY_FIELDS:
            if k in row.index:
                v = row[k]
                import math
                if v is None or (isinstance(v, float) and not math.isfinite(v)):
                    props[k] = None
                else:
                    props[k] = v.item() if hasattr(v, 'item') else v
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Point", "coordinates": [geom.x, geom.y]},
        })
    return {"type": "FeatureCollection", "features": features}


# ── interseção bacia × inventário ─────────────────────────────────────────────

def clip_stations_by_basin(watershed_geojson: dict[str, Any]) -> dict[str, list[dict]]:
    """Recebe GeoJSON da bacia e retorna estações PLU/FLU dentro, com todos os campos."""
    basin_geom = _geojson_to_geometry(watershed_geojson)
    basin_gdf  = gpd.GeoDataFrame({"_": [0]}, geometry=[basin_geom], crs="EPSG:4326")

    inv     = _load_inventory()
    clipped = gpd.clip(inv, basin_gdf)

    def _pack(df: gpd.GeoDataFrame) -> list[dict]:
        out = []
        for _, row in df.iterrows():
            d = _row_to_dict(row)
            # garante campos mínimos que o frontend usa para a lista lateral
            d.setdefault("CODIGO",    d.get(_COL_CODIGO, ""))
            d.setdefault("TIPOESTACA", d.get(_COL_TIPO, ""))
            d["lat"] = float(row.geometry.y)
            d["lng"] = float(row.geometry.x)
            out.append(d)
        return out

    pluv = clipped[clipped[_COL_TIPO].isin(_PLUV)]
    fluv = clipped[clipped[_COL_TIPO].isin(_FLUV)]
    return {"pluviometricas": _pack(pluv), "fluviometricas": _pack(fluv)}


def _geojson_to_geometry(obj: dict):
    t = obj.get("type")
    if t == "Feature":
        return shape(obj["geometry"])
    if t == "FeatureCollection":
        return unary_union([shape(f["geometry"]) for f in obj["features"]])
    return shape(obj)


# ── download de série única ────────────────────────────────────────────────────

def download_series(
    kind: str,
    codigo_estacao: str,
    pasta_saida: Path,
    identificador: str,
    senha: str,
    ano_inicial: int = 1900,
    ano_final: int = 2025,
    tipo_filtro_data: str = "DATA_LEITURA",
) -> Path:
    from ANA.ANA_Swagger_Download import Download_JSON  # noqa
    downloader = Download_JSON()
    method_name = {
        "chuva":               "D_HidroSerieChuva",
        "cota":                "D_HidroSerieCota",
        "vazao":               "D_HidroSerieVazao",
        "curva_descarga":      "D_HidroSerieCurvaDescarga",
        "perfil_transversal":  "D_HidroSeriePerfilTransversal",
        "qa":                  "D_HidroSerieQA",
        "resumo_descarga":     "D_HidroSerieResumoDescarga",
        "sedimentos":          "D_HidroSerieSedimentos",
        "granulometria":       "D_HidroSerieGranulometria",
        "telemetrica_detalhada": "D_HidroinfoanaSerieTelemetricaDetalhada",
        "telemetrica_adotada":   "D_HidroinfoanaSerieTelemetricaAdotada",
    }.get(kind)
    if not method_name:
        raise ValueError(f"kind desconhecido: {kind}")
    method = getattr(downloader, method_name, None)
    if not method:
        raise NotImplementedError(f"{method_name} não existe em Download_JSON.")
    pasta_saida.mkdir(parents=True, exist_ok=True)
    method(
        identificador=identificador, senha=senha,
        codigo_estacao=int(codigo_estacao), pasta_saida=str(pasta_saida),
        tipo_filtro_data=tipo_filtro_data, ano_inicial=ano_inicial, ano_final=ano_final,
    )
    return pasta_saida


def process_series(kind: str, pasta_json: Path, pasta_csv: Path) -> Path:
    from ANA.ANA_Swagger_Processamento import Processamento_JSON  # noqa
    processer = Processamento_JSON()
    method_name = {
        "chuva":               "P_HidroSerieChuva",
        "cota":                "P_HidroSerieCota",
        "vazao":               "P_HidroSerieVazao",
        "curva_descarga":      "P_HidroSerieCurvaDescarga",
        "perfil_transversal":  "P_HidroSeriePerfilTransversal",
        "qa":                  "P_HidroSerieQA",
        "resumo_descarga":     "P_HidroSerieResumoDescarga",
        "sedimentos":          "P_HidroSerieSedimentos",
        "telemetrica_detalhada": "P_HidroinfoanaSerieTelemetricaDetalhada",
        "telemetrica_adotada":   "P_HidroinfoanaSerieTelemetricaAdotada",
    }.get(kind)
    if not method_name:
        raise ValueError(f"kind sem processamento: {kind}")
    method = getattr(processer, method_name, None)
    if not method:
        raise NotImplementedError(f"{method_name} não existe em Processamento_JSON.")
    pasta_csv.mkdir(parents=True, exist_ok=True)
    method(pasta_json=str(pasta_json), pasta_saida_csv=str(pasta_csv))
    return pasta_csv
