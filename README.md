# ATS Tutorials

Minimal, runnable [ArcGIS Maps SDK for JavaScript](https://developers.arcgis.com/javascript/latest/) samples that go with the **ATS Build** episodes on the All Things Spatial YouTube channel.

Each sample is the smallest app that shows one technique from one episode. You can clone it, run it and read it in a few minutes.

## Layout

```
samples/
  00-hello-map/     # keyless starter: a map that loads with no API key
  01-usgs-earthquakes/  # the live USGS earthquake feed in a GeoJSONLayer (BLD-S01E01)
  02-imagery-swipe/     # before/after Landsat imagery with the arcgis-swipe component (BLD-S01E02)
  03-clip-geotiff/      # draw a box, clip USGS 3DEP elevation, save a GeoTIFF (BLD-S01E03)
  04-custom-map-controls/  # your own zoom, home and basemap buttons, no widgets (BLD-S01E04)
  05-geoparquet-parquetlayer/  # Overture places GeoParquet in a ParquetLayer (beta): filter, query, hitTest (BLD-S02E01)
  <nn-topic>/       # one folder per episode sample, added with the episode
scripts/
  smoke.mjs         # headless smoke test that CI runs against every sample
  content-scan.mjs  # forbidden-content scan that CI runs on every push
```

Each sample is a self-contained Vite project with its own `package.json` and `package-lock.json`. The `@arcgis/core` version is pinned exactly, so a sample keeps working after the SDK moves on.

## GIS Concepts companions

Some episodes of the **GIS Concepts** series (playlist: https://www.youtube.com/playlist?list=PLHbasl_Mg-uE) also get a sample: the smallest app that shows the JavaScript technique behind the concept. These folders are named by episode code, `con-NN-<topic>`.

| Episode | Sample | Concept page |
|---|---|---|
| CON-S01E01 | [`con-01-geodesic-vs-planar`](samples/con-01-geodesic-vs-planar/): planar area on Web Mercator vs geodesic area on the ellipsoid | https://concepts.allthingsspatial.io/projection-lab/ |
| CON-S01E03 | [`con-03-renderers-by-level`](samples/con-03-renderers-by-level/): nominal, ordinal, interval and ratio renderers on one county layer | https://concepts.allthingsspatial.io/measurement-lab/ |

## Run a sample

You need Node.js 20 or later.

```bash
git clone https://github.com/allthingsspatial-samples/ats-tutorials.git
cd ats-tutorials/samples/00-hello-map
npm ci
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173). To build and serve a production copy, run `npm run build` and then `npm run preview`.

No API key is needed for `00-hello-map`. If a later sample needs one, its own README says so and reads the key from a local `.env` file. That file is git-ignored: never commit a key.

## CI

`.github/workflows/ci.yml` finds every `samples/*/` folder that has a `package.json` and runs three steps on each one:

1. `npm ci`
2. `npm run build`
3. A headless smoke run (`scripts/smoke.mjs`): it serves the built `dist/` folder, opens it in headless Chrome and passes only if the page loads, the map view becomes ready, there are no console errors or failed requests, and no request carries a `token=`.

To add a sample, add a folder. You do not need to edit the CI file.

A separate `Forbidden-content scan` job (`scripts/content-scan.mjs`) checks every tracked file and every commit message for local file paths, credentials (API keys, access tokens, private keys, `.env` files) and a denylist of terms that must not appear in this repo. The denylist is stored only as salted hashes in `scripts/content-scan.denylist.json`. Findings print the file, the line and the category, never the matched text. Run it locally with `node scripts/content-scan.mjs`.

### Sample contract

For the smoke run to pass, a sample must:

- build to `dist/` with `npm run build`;
- assign its view to `window.view` (for example `window.view = view;`) so the smoke test can wait for `view.ready`.

## License

[MIT](LICENSE), copyright All Things Spatial.
