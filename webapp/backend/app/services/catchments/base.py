"""Interface de acesso aos dados MERIT-Hydro / MERIT-Basins.

Essa camada existe para isolar a fonte dos dados. O MVP usa shapefiles em disco
(ver `shapefile.py`). No futuro, quando o escopo sair da América do Sul para o
mundo inteiro, uma implementação `PostGISStore` pode substituir o `ShapefileStore`
sem alterar o resto do backend.
"""
from __future__ import annotations

from typing import Protocol

import geopandas as gpd


class CatchmentStore(Protocol):
    """Contrato mínimo que qualquer fonte de dados MERIT precisa cumprir."""

    def get_megabasins(self) -> gpd.GeoDataFrame:
        """GeoDataFrame das 61 megabacias Pfafstetter nível 2 (campos: BASIN, geometry)."""
        ...

    def get_catchments(self, basin: int, *, high_res: bool) -> gpd.GeoDataFrame:
        """Unit catchments da megabacia `basin`. Index = COMID."""
        ...

    def get_rivers(self, basin: int) -> gpd.GeoDataFrame:
        """River flowlines da megabacia `basin`. Index = COMID."""
        ...
