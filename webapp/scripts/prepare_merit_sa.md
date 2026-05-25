# Checklist de dados MERIT — América do Sul

O backend não funciona sem estes dados. São arquivos grandes (dezenas de GB)
e devem ser baixados uma única vez. A estrutura final esperada fica em
`webapp/data/` (configurável via `MERIT_ROOT`).

## Estrutura final esperada

```
webapp/data/
├── shp/
│   ├── basins_level2/
│   │   └── merit_hydro_vect_level2.{shp,shx,dbf,prj}
│   ├── merit_catchments/
│   │   └── cat_pfaf_<NN>_MERIT_Hydro_v07_Basins_v01.{shp,shx,dbf,cpg}
│   ├── catchments_simplified/
│   │   └── cat_pfaf_<NN>_MERIT_Hydro_v07_Basins_v01.{shp,shx,dbf,prj}
│   └── rivers/
│       └── riv_pfaf_<NN>_MERIT_Hydro_v07_Basins_v01.{shp,shx,dbf,prj}
└── raster/
    ├── flowdir_basins/flowdir<NN>.tif
    └── accum_basins/accum<NN>.tif
```

`<NN>` = código Pfafstetter nível 2. **América do Sul = 61, 62, 63, 64, 65, 66, 67**.

> **Atenção à nomenclatura dos rasters**: o backend monta o caminho como
> `"{flowdir_dir}/flowdir{basin}.tif"` (ver `app/lib/delineator/merit_detailed.py`).
> Os arquivos baixados em mghydro.com já vêm nesse formato — basta colocar na
> pasta certa, não renomear.

> **Atenção aos shapefiles `cat_pfaf_*`**: o ZIP que você baixa em reachhydro.org
> vem com sufixo `_bugfix1` (ex.: `cat_pfaf_61_MERIT_Hydro_v07_Basins_v01_bugfix1.shp`).
> Esse sufixo precisa ser **removido** antes de jogar em `merit_catchments/`.

## Status das bacias 61–67 (América do Sul)

Após os passos abaixo, rode `python -m scripts.check_data` (ainda não escrito)
ou simplesmente confira:

| Item | Bacias 61–67 prontas? |
|------|----------------------|
| `raster/flowdir_basins/flowdir<NN>.tif` | ✓ se você seguiu o passo 5 |
| `raster/accum_basins/accum<NN>.tif`     | ✓ se você seguiu o passo 5 |
| `shp/merit_catchments/cat_pfaf_<NN>...` | ✓ se você seguiu o passo 3 |
| `shp/catchments_simplified/cat_pfaf_<NN>...` | ✓ se você seguiu o passo 4 |
| `shp/rivers/riv_pfaf_<NN>...`           | **necessário, ainda não baixado** |
| `shp/basins_level2/merit_hydro_vect_level2.shp` | ✓ se você seguiu o passo 1 |

## Passo 1 — Megabacias nível 2 (pequeno, sempre obrigatório)

Arquivo pequeno (~5 MB), cobre o mundo todo. Fonte:
https://github.com/mheberger/delineator/tree/main/data/shp/basins_level2

Baixar os 4 arquivos (`.shp`, `.shx`, `.dbf`, `.prj`) e jogar em
`webapp/data/shp/basins_level2/`.

## Passo 2 — Identificar bacias

América do Sul é coberta pelas megabacias `61, 62, 63, 64, 65, 66, 67`. Coloque
isso em `PRELOAD_BASINS` no `.env`.

## Passo 3 — Catchments hi-res (MERIT-Basins, reachhydro.org)

Fonte: https://www.reachhydro.org/home/params/merit-basins → pasta `pfaf_level_02/`.

Baixar `cat_pfaf_<NN>_MERIT_Hydro_v07_Basins_v01_bugfix1.zip` para cada bacia
(7 arquivos no total para a AS).

Descompactar **e remover o sufixo `_bugfix1`**:

```bash
# de dentro de webapp/
for f in cat_pfaf_6/cat_pfaf_*_bugfix1.*; do
  mv "$f" "data/shp/merit_catchments/$(basename "${f/_bugfix1/}")"
done
```

## Passo 4 — Catchments simplificados (mghydro)

Fonte única: https://mghydro.com/watersheds/share/catchments_simplified.zip

O ZIP traz **todas** as 61 megabacias do mundo. Você pode descompactar tudo de
uma vez em `data/shp/catchments_simplified/` — o backend só carrega as que
forem usadas. Esse conjunto é obrigatório para bacias grandes
(área > `LOW_RES_THRESHOLD`, default 50.000 km²).

## Passo 5 — Rasters (high-res)

Fonte: https://mghydro.com/watersheds/rasters

Para cada bacia 61–67, baixar `flowdir<NN>.tif` e `accum<NN>.tif` e jogar nas
pastas `data/raster/flowdir_basins/` e `data/raster/accum_basins/`. Tamanho
total da AS: ~3,5 GB de flowdir + ~3,1 GB de accum.

## Passo 6 — Rios (necessário para qualquer delineação)

**Obrigatório**, sem isso o `_collect_upstream` falha. Mesma fonte do passo 3
(reachhydro.org → pfaf_level_02). Baixar `riv_pfaf_<NN>_MERIT_Hydro_v07_Basins_v01.zip`
para as 7 bacias da AS, descompactar em `data/shp/rivers/`.

Se os arquivos vierem com sufixo `_bugfix1`, repita a remoção do passo 3.

## Passo 7 — Primeiro boot

```bash
cd webapp/backend
uvicorn app.main:app --reload --reload-dir app
```

No primeiro request de uma bacia, o sistema lê o shapefile, gera um pickle em
`$PICKLE_DIR` e cacheia em RAM. Próximos requests da mesma bacia são ~instantâneos.

Se preferir pré-carregar tudo no boot (mais lento mas elimina latência depois),
defina `PRELOAD_BASINS=61,62,63,64,65,66,67` no `.env`.
