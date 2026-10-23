# 04 Custom Map Controls

Zoom, home and basemap buttons of your own on an ArcGIS map component, with no widget and no view model. It goes with the ATS Build episode BLD-S01E04, "Custom Map Controls After the Widget Deprecation (ArcGIS JS 5.0)".

- Why: as of 5.0 all widgets are deprecated (release notes), `MapView.ui` is deprecated since 5.1, and the widget view model roadmap lists `ZoomViewModel` for removal, pointing to `canZoomIn`, `canZoomOut`, `zoomIn()` and `zoomOut()` on the Map component instead.
- Map: one `arcgis-map` element on the `satellite` basemap over the Grand Canyon. `satellite` and `topo-vector` are 2D legacy basemap ids; the sample sets no API key.
- Controls: a plain `<nav>` with four buttons in the map's `top-right` slot. Icons are Lucide icons (ISC license, https://lucide.dev/license) written inline as SVG.
- Zoom: `mapElement.zoomIn()` and `mapElement.zoomOut()`. The buttons are disabled from `canZoomIn` / `canZoomOut` on every `arcgisViewChange` event; `constraints.minZoom` is 9.
- Home: the starting `viewpoint`, cloned after `viewOnReady()`, passed to `goTo()`.
- Basemap: one button that sets `mapElement.basemap` to `satellite` or `topo-vector`.
- Attribution: left on, as Esri requires for its basemaps.
- SDK: `@arcgis/core` and `@arcgis/map-components` 5.1.27 (pinned). It also builds and runs on 5.0.19.
- Build tool: Vite

```bash
npm ci
npm run dev
```

Everything is in `index.html` and `src/main.js`. See the same pattern in a full app: https://www.allthingsspatial.io/pages/fire-line/
