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

    # Paths relativos são resolvidos contra webapp/ (não contra o CWD do uvicorn).
    merit_root: Path = Field(default=Path("data"))
    pickle_dir: Path = Field(default=Path("backend/storage/pickles"))
    preload_basins: str = Field(default="")

    ana_inventory_path: Path = Field(default=Path("backend/storage/estacoes_ana.gpkg"))
    ana_identificador: str = Field(default="")
    ana_senha: str = Field(default="")

    low_res_threshold: float = Field(default=50000.0)
    search_dist: float = Field(default=0.005)
    fill_holes: bool = Field(default=True)
    fill_threshold: int = Field(default=100)

    huey_db_path: Path = Field(default=Path("backend/storage/jobs.db"))
    huey_immediate: bool = Field(default=False)

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

    @field_validator("merit_root", "pickle_dir", "ana_inventory_path", "huey_db_path", mode="after")
    @classmethod
    def _abs_path(cls, v: Path) -> Path:
        return _resolve(v)

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
