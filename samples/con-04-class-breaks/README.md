# con-04 Class Breaks

One layer of the 254 Texas counties, colored by people per km². Pick a classification method (natural breaks, quantile, equal interval, standard deviation) and a number of classes (3-7), and the sample asks the SDK for the breaks and applies them as a `ClassBreaksRenderer`. It goes with the GIS Concepts episode CON-S01E04, on data classification (natural breaks vs quantile).

- What it teaches: the same data cut four ways gives four different maps. Population density is very skewed (a few metro counties, many nearly empty ones), so equal interval puts almost every county in class 1, quantile spreads the colors evenly, and natural breaks follows the gaps in the data.
- Breaks: `classBreaks()` from `@arcgis/core/smartMapping/statistics/classBreaks.js`, with `classificationMethod` and `numClasses`. The layer is a client-side `GeoJSONLayer`, so the sample zooms to the whole state first and passes `view` and `useFeaturesInView: true`: the statistics come from the features in the view, with no request to a server.
- Standard deviation: `standardDeviationInterval: 1` gives classes one standard deviation wide, the middle one centered on the mean, so the data sets the number of classes and the picker is disabled. On this skewed data the classes below the mean fall under zero; the sample drops the ones that hold no data.
- Renderer: a `ClassBreaksRenderer` built from the returned `classBreakInfos`, with a yellow-to-purple ramp sampled to the number of classes. Legend: the `arcgis-legend` component.
- Basemap: `gray-vector`, a 2D (legacy) basemap id. No API key.
- SDK: `@arcgis/core` and `@arcgis/map-components` 5.1.27 (pinned). API reference: https://developers.arcgis.com/javascript/latest/references/core/smartMapping/statistics/classBreaks/ and https://developers.arcgis.com/javascript/latest/references/core/renderers/ClassBreaksRenderer/
- Build tool: Vite

```bash
npm ci
npm run dev
```

Everything is in `index.html` and `src/main.js`. The same data classified in Python with mapclassify: [`python/con-04-mapclassify-breaks`](../../python/con-04-mapclassify-breaks/). Esri's natural breaks and mapclassify's Fisher-Jenks can place some breaks differently on the same data.

## Data

`public/data/texas-counties.geojson` holds the 254 Texas counties. `scripts/build-data.py` builds it from two public US Census Bureau files (needs `pip install pyshp`):

| Field | Source |
|---|---|
| geometry, `GEOID`, `NAME`, `LAND_KM2` | US Census Bureau, Cartographic Boundary Files, counties 1:20,000,000, 2023: https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_20m.zip |
| `POP2024` | US Census Bureau, Population Estimates Program, county totals, Vintage 2024 (July 1, 2024): https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv |
| `DENSITY` | `POP2024` / `LAND_KM2` (people per km² of land) |

```bash
python scripts/build-data.py cb_2023_us_county_20m.shp co-est2024-alldata.csv public/data/texas-counties.geojson
```

The county outlines are NAD83; at 1:20m the difference from WGS84 is far below what the map can show.

Explore the same idea interactively on the Classification concept page, https://concepts.allthingsspatial.io/concepts/classification/. All GIS Concepts episodes: https://www.youtube.com/playlist?list=PLHbasl_Mg-uE

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
