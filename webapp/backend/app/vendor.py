"""Expõe `delineator-main/` e `Swagger-ANA-main/` ao import system.

Esses dois projetos não têm pyproject/setup.py, então não dá para `pip install -e`.
A alternativa limpa é prepender ao `sys.path` uma única vez no boot.
Depois disso, `from py.fast_dissolve import ...` e `from ANA.ANA_Swagger_Download import ...`
funcionam normalmente.

`configure_delineator()` injeta nossos paths/configs nos globals do `config.py`
do delineator e dos módulos que já tenham feito `from config import *`.
"""
from __future__ import annotations

import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
# webapp/backend/app/vendor.py -> webapp/backend/app -> webapp/backend -> webapp -> DownloaderHydro
_PROJECT_ROOT = _THIS.parents[3]

DELINEATOR_ROOT = _PROJECT_ROOT / "delineator-main"
SWAGGER_ANA_ROOT = _PROJECT_ROOT / "Swagger-ANA-main"


def install() -> None:
    for p in (DELINEATOR_ROOT, SWAGGER_ANA_ROOT):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)


def configure_delineator() -> None:
    """Sobrescreve os globals do `config.py` do delineator com nossos Settings.

    Idempotente. Pode (e deve) ser chamado antes de qualquer import de
    `py.merit_detailed` ou `py.fast_dissolve`. Se esses módulos já tiverem sido
    importados, faz monkeypatch também nos namespaces deles (porque o
    `from config import *` captura os valores no momento do import).
    """
    from app.settings import settings

    overrides = {
        "MERIT_FDIR_DIR": str(settings.flowdir_dir),
        "MERIT_ACCUM_DIR": str(settings.accum_dir),
        "HIGHRES_CATCHMENTS_DIR": str(settings.highres_catchments_dir),
        "LOWRES_CATCHMENTS_DIR": str(settings.lowres_catchments_dir),
        "RIVERS_DIR": str(settings.rivers_dir),
        "PICKLE_DIR": str(settings.pickle_dir),
        "OUTPUT_DIR": str(settings.pickle_dir.parent / "output"),
        "MAP_FOLDER": str(settings.pickle_dir.parent / "map"),
        "OUTLETS_CSV": "",
        "VERBOSE": False,
        "PLOTS": False,
        "MAKE_MAP": False,
        "MAP_RIVERS": False,
        "OUTPUT_CSV": False,
        "OUTPUT_EXT": "",
        "HIGH_RES": True,
        "LOW_RES_THRESHOLD": settings.low_res_threshold,
        "SEARCH_DIST": settings.search_dist,
        "FILL": settings.fill_holes,
        "FILL_THRESHOLD": settings.fill_threshold,
        "SIMPLIFY": False,
        "SIMPLIFY_TOLERANCE": 0.0008,
        "MATCH_AREAS": False,
        "AREA_MATCHING_THRESHOLD": 0.25,
        "MAX_DIST": 0.075,
        "NUM_STREAM_ORDERS": 3,
        "THRESHOLD_SINGLE": 500,
        "THRESHOLD_MULTIPLE": 5000,
    }

    import config as _cfg  # módulo do delineator-main
    for k, v in overrides.items():
        setattr(_cfg, k, v)

    # Se algum módulo do delineator já fez `from config import *`, propagar.
    for modname in ("py.merit_detailed", "py.fast_dissolve", "py.mapper", "py.raster_plots"):
        mod = sys.modules.get(modname)
        if mod is None:
            continue
        for k, v in overrides.items():
            if hasattr(mod, k):
                setattr(mod, k, v)
