"""Configuração do backend (lê variáveis do `.env` via pydantic-settings).

Este módulo absorve todos os knobs que antes viviam no `delineator-main/config.py`
(originalmente CLI). Os comentários com a justificativa de cada valor estão no
`.env.example`. As propriedades `*_dir` derivam de `merit_root` e seguem o
layout de pastas que `webapp/scripts/prepare_merit_sa.md` documenta.
"""
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# webapp/backend/app/settings.py -> webapp/backend/app -> webapp/backend -> webapp
WEBAPP_ROOT = Path(__file__).resolve().parents[2]


def _resolve(p: Path) -> Path:
    """Resolve um Path: se relativo, ancora no diretório webapp/."""
    return p if p.is_absolute() else (WEBAPP_ROOT / p).resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- Dados MERIT-Hydro / MERIT-Basins ----
    # Paths relativos são resolvidos contra webapp/ (não contra o CWD do uvicorn).
    merit_root: Path = Field(default=Path("data"))
    pickle_dir: Path = Field(default=Path("backend/storage/pickles"))
    preload_basins: str = Field(default="")

    # ---- Inventário e credenciais ANA ----
    ana_inventory_path: Path = Field(default=Path("backend/storage/estacoes_ana.gpkg"))
    ana_identificador: str = Field(default="")
    ana_senha: str = Field(default="")

    # ---- Delineação (knobs originais do delineator/config.py) ----
    # Acima desse limiar de área a delineação cai pra modo low-res.
    low_res_threshold: float = Field(default=50000.0)
    # Distância máxima (graus) pra "snap" do exutório a uma megabacia/catchment.
    search_dist: float = Field(default=0.005)
    # Preencher buracos no polígono final?
    fill_holes: bool = Field(default=True)
    # Tamanho máximo (em pixels da grade 3"") de buracos a preencher.
    fill_threshold: int = Field(default=100)
    # Mínimo de pixels a montante pra um pixel ser considerado "rio" no snap
    # quando a bacia tem 1 só unit catchment (cabeceira pequena).
    threshold_single: int = Field(default=500)
    # Idem, mas com múltiplas unit catchments (rio principal). Valor maior evita
    # snap em afluentes pequenos próximos.
    threshold_multiple: int = Field(default=5000)
    # Quantos stream orders mais altos incluir no GeoJSON de rivers.
    num_stream_orders: int = Field(default=3)
    # Tolerância (graus) do simplify, usado se DelineateRequest.simplify=True.
    simplify_tolerance: float = Field(default=0.0008)

    # ---- Fila de downloads (huey) ----
    huey_db_path: Path = Field(default=Path("backend/storage/jobs.db"))
    huey_immediate: bool = Field(default=False)

    # ---- Servidor ----
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")
    # Chave secreta para assinar cookies de sessão. Troque por valor aleatório em produção.
    secret_key: str = Field(default="dev-insecure-key-change-in-production")

    @field_validator("merit_root", "pickle_dir", "ana_inventory_path", "huey_db_path", mode="after")
    @classmethod
    def _abs_path(cls, v: Path) -> Path:
        return _resolve(v)

    # ---- Paths derivados ----
    @property
    def basins_level2_shp(self) -> Path:
        return self.merit_root / "shp" / "basins_level2" / "merit_hydro_vect_level2.shp"

    @property
    def highres_catchments_dir(self) -> Path:
        return self.merit_root / "shp" / "merit_catchments"

    @property
    def lowres_catchments_dir(self) -> Path:
        return self.merit_root / "shp" / "catchments_simplified"

    @property
    def rivers_dir(self) -> Path:
        return self.merit_root / "shp" / "rivers"

    @property
    def flowdir_dir(self) -> Path:
        return self.merit_root / "raster" / "flowdir_basins"

    @property
    def accum_dir(self) -> Path:
        return self.merit_root / "raster" / "accum_basins"

    @property
    def preload_basins_list(self) -> list[int]:
        if not self.preload_basins.strip():
            return []
        return [int(b.strip()) for b in self.preload_basins.split(",") if b.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
