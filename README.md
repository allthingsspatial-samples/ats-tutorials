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
  <nn-topic>/       # one folder per episode sample, added with the episode
scripts/
  smoke.mjs         # headless smoke test that CI runs against every sample
```

Each sample is a self-contained Vite project with its own `package.json` and `package-lock.json`. The `@arcgis/core` version is pinned exactly, so a sample keeps working after the SDK moves on.

## Run a sample

You need Node.js 20 or later.

```bash
git clone https://github.com/allthingsspatial/ats-tutorials.git
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

### Sample contract

For the smoke run to pass, a sample must:

- build to `dist/` with `npm run build`;
- assign its view to `window.view` (for example `window.view = view;`) so the smoke test can wait for `view.ready`.

## License

[MIT](LICENSE), copyright All Things Spatial.
