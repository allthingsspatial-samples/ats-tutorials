# 05 GeoParquet on a Web Map

Load a GeoParquet file into an ArcGIS map component with `ParquetLayer`, style it, filter it, query it, and load larger files to see how far it goes. It goes with the ATS Build episode BLD-S02E01, "GeoParquet on a Web Map: ParquetLayer in ArcGIS Maps SDK 5.1".

`ParquetLayer` is **beta** in ArcGIS Maps SDK for JavaScript 5.1 (API reference: https://developers.arcgis.com/javascript/latest/references/core/layers/ParquetLayer/). Behavior can change between releases.

- Data: places from the Overture Maps Foundation (https://overturemaps.org), places theme, release `2026-10-21.0`. Overture's Places guide: "The theme is published under the CDLA Permissive 2.0 and Apache 2.0 licenses." `public/data/denver-places.parquet` holds 120,067 places in a box around Denver.
- Why an extract: the Overture release files are ZSTD-compressed, and the ParquetLayer reference says files "must use either GZIP or Snappy compression, or no compression". `scripts/extract.py` reads one bounding box straight from Overture's public S3 bucket with DuckDB and writes it again with Snappy compression, WKB point geometry and GeoParquet 1.1 `geo` metadata.
- Layer: `new ParquetLayer({ data: new ParquetFilesData({ urls }) })`. In our tests on 5.1.27 the points only drew once `geometryEncoding` (`GeometryEncodingWkb`, field `geometry`), `spatialReference` (4326) and `geometryType` (`point`) were set on the layer, so the sample sets all three.
- Style: a unique-value renderer on the `category` field.
- Filter: `definitionExpression` on the layer (new in 5.1). The map and every query follow it.
- Queries: `queryFeatureCount()`, a statistics query (count per category, `groupByFieldsForStatistics`) and a `returnDistinctValues` query. The reference lists `orderByFields` for datasets of up to 500,000 features; past that the sample catches the refusal, says so in the panel and sorts in the browser.
- hitTest: a click lists every place under the cursor (5.1 returns all hit features, not only the topmost), with names looked up by object ID.
- SDK: `@arcgis/core` and `@arcgis/map-components` 5.1.27 (pinned). No API key.
- Build tool: Vite

```bash
npm ci
npm run dev
```

To try larger files (needs Python with `pip install duckdb pyarrow`; each run reads from Overture's public bucket):

```bash
python scripts/extract.py colorado -109.06 36.99 -102.04 41.01
python scripts/extract.py four-corners -114.05 31.33 -102.04 41.01
```

Then pick the file in the panel. The boxes are rectangles, so they include the edges of neighbouring states. Those files are git-ignored.

Everything is in `index.html` and `src/main.js`.
