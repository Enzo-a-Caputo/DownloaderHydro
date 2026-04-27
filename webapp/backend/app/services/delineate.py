"""Delineação de bacia para um único ponto — função pura, sem efeitos colaterais.

Derivada de `delineator-main/delineate.py::delineate()`, mas:
- recebe (lat, lng) em vez de ler CSV
- retorna dicts GeoJSON em vez de gravar arquivos
- não usa `from config import *` — lê de `app.settings`
- reaproveita `py.fast_dissolve` e `py.merit_detailed` do delineator original (via vendor)
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from typing import Literal

import geopandas as gpd
import numpy as np
import pyproj
from shapely.geometry import MultiPolygon, Point, Polygon, box

from app.services.catchments.base import CatchmentStore
from app.settings import settings

PROJ_WGS84 = "EPSG:4326"


@dataclass
class DelineationResult:
    watershed_geojson: dict   # GeoJSON Feature
    rivers_geojson: dict | None
    area_km2: float
    lat_snap: float
    lng_snap: float
    snap_dist_m: float
    basin_pfaf2: int
    mode: Literal["high", "low"]


def _area_km2(poly) -> float:
    geod = pyproj.Geod(ellps="WGS84")
    area_m2, _ = geod.geometry_area_perimeter(poly)
    return abs(area_m2) / 1e6


def _close_holes(poly, area_max: float):
    """Reimplementação compatível com Shapely 2.x do `close_holes` do delineator.

    O original em `py/fast_dissolve.py` usa `for sub_poly in poly:` em MultiPolygon,
    padrão removido em Shapely 2.0 (usar `.geoms`). Mantemos `delineator-main/`
    intocado e replicamos a lógica aqui.
    """
    if isinstance(poly, Polygon):
        if area_max == 0:
            return Polygon(list(poly.exterior.coords)) if poly.interiors else poly
        keep = [r for r in poly.interiors if Polygon(r).area > area_max]
        return Polygon(poly.exterior.coords, holes=keep)
    if isinstance(poly, MultiPolygon):
        return MultiPolygon([_close_holes(p, area_max) for p in poly.geoms])
    raise ValueError(f"Geometria não suportada em _close_holes: {type(poly).__name__}")


def _collect_upstream(rivers_gdf: gpd.GeoDataFrame, start_comid: int) -> list[int]:
    """Versão iterativa (não recursiva) do `addnode` original.
    Mais segura para bacias grandes — recursão estoura stack em ~1000 níveis.
    """
    comids: list[int] = []
    stack = [start_comid]
    while stack:
        node = stack.pop()
        comids.append(node)
        row = rivers_gdf.loc[node]
        for col in ("up1", "up2", "up3", "up4"):
            up = row[col]
            if up != 0:
                stack.append(up)
    return comids


def _find_close_catchment(rivers_gdf: gpd.GeoDataFrame, lat: float, lng: float,
                          area_reported: float, max_dist: float = 0.075,
                          threshold: float = 0.25) -> tuple[int | None, float | None]:
    """Relocar pour point para um reach com área similar à reportada.
    Idêntico ao original, só movido para fora do closure.
    """
    dist = 0.01
    last_count = 0
    while True:
        bbox = box(lng - dist, lat - dist, lng + dist, lat + dist)
        idxs = list(rivers_gdf.sindex.intersection(bbox.bounds))
        candidates = rivers_gdf.iloc[idxs]
        precise = candidates[candidates.intersects(bbox)]
        if len(precise) > last_count:
            precise = precise.copy()
            precise["pd"] = ((precise["uparea"] - area_reported) / area_reported).abs()
            min_pd = precise["pd"].min()
            if min_pd < threshold:
                comid = precise["pd"].idxmin()
                return comid, float(precise.loc[comid, "uparea"])
            last_count = len(precise)
        if dist > max_dist:
            return None, None
        dist += 0.01


def delineate_point(
    lat: float,
    lng: float,
    store: CatchmentStore,
    *,
    precision: Literal["high", "low", "auto"] = "auto",
    simplify: bool = False,
    simplify_tol: float = 0.0008,
    fill: bool = True,
    fill_threshold_px: int = 100,
    include_rivers: bool = True,
    num_stream_orders: int = 3,
) -> DelineationResult:
    """Delineia a bacia a montante de (lat, lng).

    Raises:
        ValueError: se o ponto não cai em nenhuma bacia Pfafstetter nível 2,
                    ou não acha unit catchment dentro de SEARCH_DIST.
    """
    # -- 1. identificar megabacia pfaf-2 --
    megabasins = store.get_megabasins()
    point = Point(lng, lat)
    point_gdf = gpd.GeoDataFrame({"_": [0]}, geometry=[point], crs=PROJ_WGS84)

    search = settings.search_dist
    if search == 0:
        joined = gpd.sjoin(point_gdf, megabasins, how="left", predicate="intersects")
    else:
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=UserWarning)
            joined = gpd.sjoin_nearest(point_gdf, megabasins, how="left", max_distance=search)

    if joined.empty or joined.iloc[0].get("BASIN") is None or np.isnan(joined.iloc[0]["BASIN"]):
        raise ValueError(f"Ponto ({lat}, {lng}) não cai em nenhuma megabacia MERIT.")

    basin = int(joined.iloc[0]["BASIN"])

    # -- 2. carregar catchments+rivers da megabacia --
    want_high = precision != "low"
    catchments = store.get_catchments(basin, high_res=want_high)
    rivers = store.get_rivers(basin)

    # -- 3. encontrar terminal comid --
    # sjoin_nearest devolve o índice do gdf da direita numa coluna nomeada;
    # quando o índice tem nome (no nosso caso "COMID"), o nome da coluna é esse.
    right_idx_name = catchments.index.name or "index_right"

    if search == 0:
        cjoin = gpd.sjoin(point_gdf, catchments, how="left", predicate="intersects")
    else:
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=UserWarning)
            cjoin = gpd.sjoin_nearest(point_gdf, catchments, how="left", max_distance=search)

    if cjoin.empty or right_idx_name not in cjoin.columns:
        raise ValueError(f"Não foi achado unit catchment em até {search}° de ({lat}, {lng}).")

    raw_comid = cjoin.iloc[0][right_idx_name]
    if raw_comid is None or (isinstance(raw_comid, float) and np.isnan(raw_comid)):
        raise ValueError(f"Não foi achado unit catchment em até {search}° de ({lat}, {lng}).")

    terminal_comid = int(raw_comid)

    # -- 4. modo high vs low --
    # Originalmente cairia para low-res automatico em bacias > LOW_RES_THRESHOLD,
    # mas catchments_simplified do mghydro tem topologia quebrada (gaps grandes
    # entre catchments por causa da simplificacao independente das bordas), o
    # que gera milhares de pedacos disjuntos no unary_union final.
    # Solucao: usar high-res sempre, exceto quando o usuario pediu low-res
    # explicitamente.
    up_area = float(rivers.loc[terminal_comid, "uparea"])
    mode: Literal["high", "low"] = "high" if want_high else "low"

    if mode == "low" and want_high:
        catchments = store.get_catchments(basin, high_res=False)

    # -- 5. montar lista de unit catchments a montante --
    comids = _collect_upstream(rivers, terminal_comid)
    subbasins = catchments.loc[comids].copy()

    # -- 6. em high-res, refinar o catchment terminal com raster (pysheds) --
    lat_snap: float
    lng_snap: float
    if mode == "high":
        # import tardio: só carrega pysheds se realmente for usar
        import py.merit_detailed as merit_detailed  # noqa  (from vendor)
        catchment_poly = subbasins.loc[terminal_comid].geometry
        split_poly, lat_snap, lng_snap = merit_detailed.split_catchment(
            "api", basin, lat, lng, catchment_poly, len(comids) == 1
        )
        if split_poly is None:
            raise RuntimeError("Erro na divisão raster do catchment terminal (pysheds).")
        subbasins.loc[terminal_comid, "geometry"] = split_poly
    else:
        snapped = rivers.loc[terminal_comid].geometry.coords[0]
        lng_snap, lat_snap = snapped[0], snapped[1]

    # -- 7. dissolve + fill + simplify --
    # unary_union em vez do dissolve_geopandas do delineator: o truque
    # clip+buffer nao dissolve de fato em geopandas modernos. Em high-res
    # os catchments compartilham bordas exatas (mesmo grid), entao o resultado
    # do unary_union e um poligono unico contiguo.
    from shapely.ops import unary_union as _uu
    basin_poly = _uu(list(subbasins.geometry.values))
    if fill:
        PIXEL_AREA_DEG = 0.000000695
        basin_poly = _close_holes(basin_poly, fill_threshold_px * PIXEL_AREA_DEG)
    if simplify:
        basin_poly = basin_poly.simplify(tolerance=simplify_tol)

    area_km2 = _area_km2(basin_poly)

    # -- 8. snap distance --
    geod = pyproj.Geod(ellps="WGS84")
    _, _, snap_dist_m = geod.inv(lng, lat, lng_snap, lat_snap)

    # -- 9. montar GeoJSON de saída --
    watershed_feature = {
        "type": "Feature",
        "properties": {
            "area_km2": round(area_km2, 2),
            "basin_pfaf2": basin,
            "mode": mode,
            "lat_snap": round(lat_snap, 5),
            "lng_snap": round(lng_snap, 5),
            "snap_dist_m": round(snap_dist_m, 1),
        },
        "geometry": json.loads(
            gpd.GeoSeries([basin_poly], crs=PROJ_WGS84).to_json()
        )["features"][0]["geometry"],
    }

    rivers_fc: dict | None = None
    if include_rivers:
        myrivers = rivers.loc[comids, ["lengthkm", "order", "geometry"]].copy()
        if "order" in myrivers.columns:
            max_order = myrivers["order"].max()
            min_order = max_order - num_stream_orders
            myrivers = myrivers[myrivers["order"] >= min_order]
        rivers_fc = json.loads(myrivers.to_json())

    return DelineationResult(
        watershed_geojson=watershed_feature,
        rivers_geojson=rivers_fc,
        area_km2=area_km2,
        lat_snap=lat_snap,
        lng_snap=lng_snap,
        snap_dist_m=snap_dist_m,
        basin_pfaf2=basin,
        mode=mode,
    )
