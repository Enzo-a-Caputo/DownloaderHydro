"""Expõe `Swagger-ANA-main/` ao import system.

O Swagger-ANA não tem `pyproject.toml`/`setup.py`, então não dá pra `pip install -e`.
A alternativa limpa é prepender ao `sys.path` uma única vez no boot. Depois disso,
`from ANA.ANA_Swagger_Download import ...` etc. funcionam normalmente.

(Histórico: este módulo originalmente também injetava o `delineator-main/` no path
e fazia monkeypatch dos globals do `config.py` dele. Esse código todo foi
absorvido para dentro do backend — ver `app/lib/delineator/` e `app/settings.py`.
Hoje só sobra o Swagger-ANA aqui.)
"""
from __future__ import annotations

import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
# webapp/backend/app/vendor.py -> webapp/backend/app -> webapp/backend -> webapp -> DownloaderHydro
_PROJECT_ROOT = _THIS.parents[3]

SWAGGER_ANA_ROOT = _PROJECT_ROOT / "Swagger-ANA-main"


def install() -> None:
    sp = str(SWAGGER_ANA_ROOT)
    if sp not in sys.path:
        sys.path.insert(0, sp)
