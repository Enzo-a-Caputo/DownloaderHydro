"""Implementação shapefile + pickle do CatchmentStore.

Espelha a lógica do `load_gdf` + cache de pickle do delineator original
(Matthew Heberger, mghydro), com a leitura de paths feita por `app.settings`
em vez de globals do `config.py`.
"""
from __future__ import annotations

import pickle
import threading
from pathlib import Path

import geopandas as gpd

from app.settings import settings

PROJ_WGS84 = "EPSG:4326"


class ShapefileStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._catchments: dict[tuple[int, bool], gpd.GeoDataFrame] = {}
        self._rivers: dict[int, gpd.GeoDataFrame] = {}
        self._megabasins: gpd.GeoDataFrame | None = None
        settings.pickle_dir.mkdir(parents=True, exist_ok=True)

    # ---- megabasins ----
    def get_megabasins(self) -> gpd.GeoDataFrame:
        if self._megabasins is not None:
            return self._megabasins
        with self._lock:
            if self._megabasins is not None:
                return self._megabasins
            shp = settings.basins_level2_shp
            if not shp.is_file():
                raise FileNotFoundError(f"Megabacias não encontradas: {shp}")
            gdf = gpd.read_file(shp).to_crs(PROJ_WGS84)
            self._megabasins = gdf
            return gdf

    # ---- catchments ----
    def get_catchments(self, basin: int, *, high_res: bool) -> gpd.GeoDataFrame:
        key = (basin, high_res)
        if key in self._catchments:
            return self._catchments[key]
        with self._lock:
            if key in self._catchments:
                return self._catchments[key]
            gdf = self._load("catchments", basin, high_res)
            self._catchments[key] = gdf
            return gdf

    # ---- rivers ----
    def get_rivers(self, basin: int) -> gpd.GeoDataFrame:
        if basin in self._rivers:
            return self._rivers[basin]
        with self._lock:
            if basin in self._rivers:
                return self._rivers[basin]
            gdf = self._load("rivers", basin, high_res=True)
            self._rivers[basin] = gdf
            return gdf

    # ---- helpers ----
    def _pickle_path(self, geotype: str, basin: int, high_res: bool) -> Path:
        suffix = "hires" if high_res else "lores"
        return settings.pickle_dir / f"{geotype}_{basin}_{suffix}.pkl"

    def _load(self, geotype: str, basin: int, high_res: bool) -> gpd.GeoDataFrame:
        pkl = self._pickle_path(geotype, basin, high_res)
        if pkl.is_file():
            with pkl.open("rb") as f:
                gdf = pickle.load(f)
            return gdf

        if geotype == "catchments":
            root = settings.highres_catchments_dir if high_res else settings.lowres_catchments_dir
            shp = root / f"cat_pfaf_{basin}_MERIT_Hydro_v07_Basins_v01.shp"
        elif geotype == "rivers":
            shp = settings.rivers_dir / f"riv_pfaf_{basin}_MERIT_Hydro_v07_Basins_v01.shp"
        else:
            raise ValueError(f"geotype inválido: {geotype}")

        if not shp.is_file():
            raise FileNotFoundError(f"Shapefile ausente: {shp}")

        gdf = gpd.read_file(shp)
        gdf.set_index("COMID", inplace=True)
        gdf.set_crs(PROJ_WGS84, inplace=True, allow_override=True)

        try:
            with pkl.open("wb") as f:
                pickle.dump(gdf, f)
        except Exception as e:  # cache é "nice to have", não derruba o request
            print(f"[warn] falhou ao gravar pickle {pkl}: {e}")

        return gdf
