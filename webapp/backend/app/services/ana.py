"""Camada fina sobre o Swagger-ANA.

Importa os módulos do `Swagger-ANA-main/` (via vendor) e expõe funções de alto
nível que os routers e o worker huey podem usar. A ideia é NÃO duplicar lógica:
qualquer correção feita no Swagger-ANA original se propaga pra cá.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import mapping, shape

from app.settings import settings


# ---- interseção bacia × inventário de estações --------------------------------

def clip_stations_by_basin(watershed_geojson: dict[str, Any]) -> dict[str, list[dict]]:
    """Recebe GeoJSON (Feature/Geometry/FeatureCollection) da bacia e retorna
    estações PLU/FLU que caem dentro.

    O inventário vem de `settings.ana_inventory_path`. As colunas esperadas são
    as mesmas que `achar_estacoes_pela_bacia` (v1) usa: `CODIGO`, `TIPOESTACA`.
    Se o seu .gpkg tiver schema diferente, ajuste o mapeamento aqui.
    """
    if not settings.ana_inventory_path.is_file():
        raise FileNotFoundError(
            f"Inventário ANA não encontrado: {settings.ana_inventory_path}. "
            "Gere com scripts/build_ana_inventory.py."
        )

    basin_geom = _geojson_to_geometry(watershed_geojson)
    basin_gdf = gpd.GeoDataFrame({"_": [0]}, geometry=[basin_geom], crs="EPSG:4326")

    inv = gpd.read_file(settings.ana_inventory_path).to_crs("EPSG:4326")
    clipped = gpd.clip(inv, basin_gdf)

    def _pack(df: gpd.GeoDataFrame) -> list[dict]:
        out = []
        for _, row in df.iterrows():
            out.append({
                "codigo": str(row["CODIGO"]),
                "tipo": row["TIPOESTACA"],
                "lat": float(row.geometry.y),
                "lng": float(row.geometry.x),
                "nome": row.get("NOME") or row.get("NomeEstaca") or None,
            })
        return out

    pluv = clipped[clipped["TIPOESTACA"] == "Pluviométrica"]
    fluv = clipped[clipped["TIPOESTACA"] == "Fluviométrica"]
    return {"pluviometricas": _pack(pluv), "fluviometricas": _pack(fluv)}


def _geojson_to_geometry(obj: dict):
    t = obj.get("type")
    if t == "Feature":
        return shape(obj["geometry"])
    if t == "FeatureCollection":
        geoms = [shape(f["geometry"]) for f in obj["features"]]
        from shapely.ops import unary_union
        return unary_union(geoms)
    # assume raw geometry
    return shape(obj)


# ---- download de série única (chamado pelo worker huey) ----------------------

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
    """Dispara o método D_* correspondente em `Download_JSON`.
    Retorna o caminho do JSON gerado.
    """
    from ANA.ANA_Swagger_Download import Download_JSON  # noqa (from vendor)
    downloader = Download_JSON()

    method_name = {
        "chuva": "D_HidroSerieChuva",
        "cota": "D_HidroSerieCota",
        "vazao": "D_HidroSerieVazao",
        "curva_descarga": "D_HidroSerieCurvaDescarga",
        "perfil_transversal": "D_HidroSeriePerfilTransversal",
        "qa": "D_HidroSerieQA",
        "resumo_descarga": "D_HidroSerieResumoDescarga",
        "sedimentos": "D_HidroSerieSedimentos",
        "dados": "D_HidroSerieDados",
        "telemetrica_detalhada": "D_HidroinfoanaSerieTelemetricaDetalhada",
        "telemetrica_adotada": "D_HidroinfoanaSerieTelemetricaAdotada",
    }.get(kind)

    if method_name is None:
        raise ValueError(f"kind desconhecido: {kind}")

    method = getattr(downloader, method_name, None)
    if method is None:
        raise NotImplementedError(f"{method_name} não existe em Download_JSON.")

    pasta_saida.mkdir(parents=True, exist_ok=True)
    method(
        identificador=identificador,
        senha=senha,
        codigo_estacao=int(codigo_estacao),
        pasta_saida=str(pasta_saida),
        tipo_filtro_data=tipo_filtro_data,
        ano_inicial=ano_inicial,
        ano_final=ano_final,
    )

    # o naming do Swagger-ANA é f"{prefix}_estacao_{codigo}.json"; retornamos a pasta
    # (o processamento subsequente lê a pasta inteira)
    return pasta_saida


def process_series(kind: str, pasta_json: Path, pasta_csv: Path) -> Path:
    """Chama o `Processamento_JSON.P_*` correspondente. Retorna pasta_csv."""
    from ANA.ANA_Swagger_Processamento import Processamento_JSON  # noqa (from vendor)
    processer = Processamento_JSON()

    method_name = {
        "chuva": "P_HidroSerieChuva",
        "cota": "P_HidroSerieCota",
        "vazao": "P_HidroSerieVazao",
        "curva_descarga": "P_HidroSerieCurvaDescarga",
        "perfil_transversal": "P_HidroSeriePerfilTransversal",
        "qa": "P_HidroSerieQA",
        "resumo_descarga": "P_HidroSerieResumoDescarga",
        "sedimentos": "P_HidroSerieSedimentos",
        "telemetrica_detalhada": "P_HidroinfoanaSerieTelemetricaDetalhada",
        "telemetrica_adotada": "P_HidroinfoanaSerieTelemetricaAdotada",
    }.get(kind)

    if method_name is None:
        raise ValueError(f"kind sem processamento definido: {kind}")

    method = getattr(processer, method_name, None)
    if method is None:
        raise NotImplementedError(f"{method_name} não existe em Processamento_JSON.")

    pasta_csv.mkdir(parents=True, exist_ok=True)
    method(pasta_json=str(pasta_json), pasta_saida_csv=str(pasta_csv))
    return pasta_csv
