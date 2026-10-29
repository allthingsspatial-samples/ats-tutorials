# con-01 Geodesic vs Planar Area

Measure the same country two ways and see how far apart the answers are: planar area on Web Mercator, and geodesic area on the WGS84 ellipsoid. It goes with the GIS Concepts episode CON-S01E01, "Map Projections Explained: Why Every Flat Map Is Wrong".

- What it teaches: a flat-map measurement is only as good as the projection under it. Web Mercator keeps shapes and angles locally but stretches area with latitude, so Greenland comes out about 16 times too big while DR Congo, on the equator, is within a few percent.
- Data: Greenland and DR Congo from Natural Earth 1:50m admin-0 countries (public domain, https://www.naturalearthdata.com/about/terms-of-use/). `public/data/countries.geojson` holds just those two; `scripts/extract.py` cuts them from `ne_50m_admin_0_countries.geojson` (https://github.com/nvkelso/natural-earth-vector).
- Layer: a `GeoJSONLayer`. `queryFeatures()` returns the same polygons twice, once with `outSpatialReference` 3857 (Web Mercator) and once with 4326 (WGS84).
- Planar: `areaOperator.execute(geometry, { unit: "square-kilometers" })` on the Web Mercator polygon. It is the area of the shape as drawn on the flat map.
- Geodesic: `geodeticAreaOperator.execute(geometry, { unit: "square-kilometers" })` on the WGS84 polygon, after `geodeticAreaOperator.load()`. It is the area on the ellipsoid.
- Panel: both areas and the ratio planar / geodesic. On 5.1.27 the sample prints Greenland 35.40 vs 2.17 million km² (16.30x) and DR Congo 2.36 vs 2.32 million km² (1.02x). The values are also logged to the console.
- Basemap: `gray-vector`, a 2D (legacy) basemap id. No API key.
- SDK: `@arcgis/core` and `@arcgis/map-components` 5.1.27 (pinned). API reference: https://developers.arcgis.com/javascript/latest/references/core/geometry/operators/geodeticAreaOperator/ and https://developers.arcgis.com/javascript/latest/references/core/geometry/operators/areaOperator/
- Build tool: Vite

```bash
npm ci
npm run dev
```

Everything is in `index.html` and `src/main.js`.

Explore the same idea interactively in the Projection Lab, https://concepts.allthingsspatial.io/projection-lab/. All GIS Concepts episodes: https://www.youtube.com/playlist?list=PLHbasl_Mg-uE

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
