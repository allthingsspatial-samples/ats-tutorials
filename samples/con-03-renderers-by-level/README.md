# con-03 Renderers by Level of Measurement

One layer of Colorado counties and four buttons, one per level of measurement: nominal, ordinal, interval and ratio. Each button swaps in the renderer that level allows. It goes with the GIS Concepts episode CON-S01E03, on levels of measurement in GIS (nominal, ordinal, interval, ratio).

- What it teaches: the kind of number decides the map. Categories get distinct hues, ranks get an ordered ramp, interval values get class breaks, and only ratio values (with a true zero) may also drive symbol size.
- Nominal: `UniqueValueRenderer` on `METRO` (Metro / Nonmetro), two unrelated hues.
- Ordinal: `UniqueValueRenderer` on `RUCC` (Rural-Urban Continuum Code 1-9), one class per code on a single-hue ramp, so order shows but no distance is implied.
- Interval: `ClassBreaksRenderer` on `TEMP_F`, the 1991-2020 mean annual temperature, in equal 5 °F classes with °C in the legend labels. The panel notes why ratios fail here: 50 °F is not twice as warm as 25 °F (10.0 vs -3.9 °C).
- Ratio: `ClassBreaksRenderer` on `DENSITY` (people per km²) with marker symbols, which draw at each county's centroid, plus a size visual variable on the same field.
- Legend: the `arcgis-legend` component.
- Basemap: `gray-vector`, a 2D (legacy) basemap id. No API key.
- SDK: `@arcgis/core` and `@arcgis/map-components` 5.1.27 (pinned). API reference: https://developers.arcgis.com/javascript/latest/references/core/renderers/UniqueValueRenderer/, https://developers.arcgis.com/javascript/latest/references/core/renderers/ClassBreaksRenderer/ and https://developers.arcgis.com/javascript/latest/references/core/renderers/visualVariables/SizeVariable/
- Build tool: Vite

```bash
npm ci
npm run dev
```

Everything is in `index.html` and `src/main.js`.

## Data

`public/data/colorado-counties.geojson` holds the 64 Colorado counties. `scripts/build-data.py` builds it from four public US government files (needs `pip install pyshp`):

| Field | Source |
|---|---|
| geometry, `GEOID`, `NAME`, `LAND_KM2` | US Census Bureau, Cartographic Boundary Files, counties 1:20,000,000, 2023: https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_20m.zip |
| `POP2024` | US Census Bureau, Population Estimates Program, county totals, Vintage 2024 (July 1, 2024): https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv |
| `RUCC`, `METRO` | USDA Economic Research Service, Rural-Urban Continuum Codes 2023: https://www.ers.usda.gov/data-products/rural-urban-continuum-codes (codes 1-3 are metro) |
| `TEMP_F` | NOAA NCEI nClimDiv county monthly mean temperature, `climdiv-tmpccy-v1.0.0-20261006`, averaged over 1991-2020: https://www.ncei.noaa.gov/pub/data/cirs/climdiv/ |
| `DENSITY` | `POP2024` / `LAND_KM2` |

```bash
python scripts/build-data.py cb_2023_us_county_20m.shp co-est2024-alldata.csv 2023-rural-urban-continuum-codes.csv climdiv-tmpccy-v1.0.0-20261006 public/data/colorado-counties.geojson
```

The county outlines are NAD83; at 1:20m the difference from WGS84 is far below what the map can show.

Explore the same idea interactively in the Measurement Lab, https://concepts.allthingsspatial.io/measurement-lab/. All GIS Concepts episodes: https://www.youtube.com/playlist?list=PLHbasl_Mg-uE

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
