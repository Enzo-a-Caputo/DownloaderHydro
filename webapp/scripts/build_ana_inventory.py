"""Script one-shot para gerar o GeoPackage consolidado de estações da ANA.

Uso:
    python scripts/build_ana_inventory.py --identificador LOGIN --senha SENHA \
        --saida backend/storage/estacoes_ana.gpkg

Gera um .gpkg com colunas: CODIGO, TIPOESTACA ('Pluviométrica'/'Fluviométrica'),
NOME (se disponível), geometry (ponto EPSG:4326).

STUB: preenchido na fase de dados — a implementação real usa o endpoint
`HidroInventarioEstacoes` via Swagger-ANA. Deixado como TODO para você
plugar quando for o momento.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permite rodar o script direto (webapp/scripts/build_ana_inventory.py)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import vendor  # noqa: E402
vendor.install()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identificador", required=True)
    parser.add_argument("--senha", required=True)
    parser.add_argument("--saida", required=True, type=Path)
    args = parser.parse_args()

    # TODO: usar ANA_Swagger_Base_GET para consumir HidroInventarioEstacoes,
    # iterar PLU + FLU, montar DataFrame com CODIGO/TIPOESTACA/NOME/LAT/LON,
    # converter para GeoDataFrame e salvar em GeoPackage.
    #
    # Esqueleto:
    #
    # from ANA.ANA_Swagger_Autenticacao import gerar_token_ana
    # from ANA.ANA_Swagger_Base_GET import Base_API
    # import pandas as pd, geopandas as gpd
    # from shapely.geometry import Point
    #
    # token, _ = gerar_token_ana(args.identificador, args.senha)
    # base = Base_API()
    # plu = base.get_HidroInventarioEstacoes(token, tipo="Pluviométrica", ...)
    # flu = base.get_HidroInventarioEstacoes(token, tipo="Fluviométrica", ...)
    # df = pd.concat([...])
    # gdf = gpd.GeoDataFrame(df, geometry=[Point(xy) for xy in zip(df.LON, df.LAT)], crs="EPSG:4326")
    # args.saida.parent.mkdir(parents=True, exist_ok=True)
    # gdf.to_file(args.saida, driver="GPKG")

    print("STUB: implemente quando decidir puxar o inventário da ANA.")
    print(f"Saída prevista: {args.saida}")


if __name__ == "__main__":
    main()
