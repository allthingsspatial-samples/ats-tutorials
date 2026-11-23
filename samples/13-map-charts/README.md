# 13 Charts Beside the Map

A map of U.S. counties with two live charts beside it, both built from the same layer: a histogram of median household income and a bar chart that counts counties by state. Both charts show only the counties in view, so they redraw when you pan or zoom. Select bars or bins and the matching counties are selected on the map. One switch turns on dark mode for the app and the charts. It goes with the ATS Build episode BLD-S02E09, "Charts Beside the Map in JavaScript (ArcGIS JS 5.2)".

- Data: Esri Living Atlas "ACS Median Household Income (Latest)" (item c9faa265b82848498bc0a8390c0afa65), county layer: U.S. Census Bureau American Community Survey 5-year estimates, 3,222 counties. Public, no sign-in. "Latest" means Esri moves the layer to each new ACS release (2020-2024 when this sample was written), so the numbers change about once a year.
- SDK: `@arcgis/core`, `@arcgis/map-components` and `@arcgis/charts-components` 5.2.8, `@esri/calcite-components` 5.2.1 (the version 5.2.8 asks for). All pinned exactly. No API key.
- Build tool: Vite

```bash
npm ci
npm run dev
```

## How it works

1. **One chart element.** `@arcgis/charts-components` has one chart tag, `<arcgis-chart>`, for every chart type, plus `<arcgis-charts-action-bar>` for its `action-bar` slot. There is no separate histogram tag or bar-chart tag: the chart type comes from the model. (`<arcgis-histogram>`, in `@arcgis/common-components`, is a different thing: it draws bins you compute yourself, for example with the smart mapping `histogram` statistics module.)
2. **Histogram model.** `createModel({ layer, chartType: "histogram" })` makes a model from the layer; `numericField` picks the field (`B19049_001E`, median household income). `binCount` is 32, the default; a histogram can have up to 64 bins.
3. **Bar chart model.** A second `<arcgis-chart>` gets `createModel({ layer, chartType: "barChart" })` with `xAxisField = "State"`. With no numeric field a bar chart counts features, so each bar is the number of counties in that state. `rotated` lays the bars on their side and `setSortOrder("yAxisDesc")` puts the biggest count first.
4. **Map and charts in sync.** Each chart has `reference-element="map"` (5.2), the id of the `<arcgis-map>`, which connects it to the map's view from anywhere on the page. `filter-by-view-extent` limits the chart to features in the current extent; `sync-view-selection` (5.1) shares selections with the view's selection manager, so selecting bars selects counties on the map.
5. **Dark mode.** One class, `calcite-mode-dark`, on the `<html>` element. `style.css` gives that class `color-scheme: dark`: Calcite 5.2 follows `color-scheme`, and the charts follow `calcite-mode-dark` on a parent (5.1 theming, which uses Calcite's CSS variables). The basemap is part of the map, so `main.js` swaps it too.

## Two things that tripped us up

- **Import path.** The docs import `createModel` from `@arcgis/charts-components/model/shared/setup-utils.js`. With npm and Vite, that path fails the build ("not exported"); the package exports it without `.js`: `@arcgis/charts-components/model/shared/setup-utils`.
- **Dark mode class placement.** The Vite build rewrites Calcite's `light-dark()` colors into variables that switch only through `color-scheme` rules in a stylesheet, and Calcite's colors are set on `:root`. So put the class on `<html>`, and set `color-scheme` in CSS, not as an inline style. With the class on `<body>`, nothing turned dark in our build.

## A chart saved in a web map (5.2 reference element)

5.2 can load a chart that was saved on a layer in Map Viewer, with no chart settings in code:

```html
<arcgis-chart reference-element="map" map-layer-id="acs-counties" chart-index="0"></arcgis-chart>
```

To use it, create a chart on the county layer in Map Viewer and save the web map, share it publicly, and set `WEBMAP_ID` in `main.js`. `LAYER_ID` must be the layer's id inside the web map. `chart-index` picks the chart when the layer has more than one. With `WEBMAP_ID` empty (the default) the third chart is left out.

## Smoke test

The smoke test, a quick automatic check that the sample loads with no errors, opens the built sample in headless Chrome and fails on any console error, failed request or `token=` request. `smoke.checks.mjs` also waits for `window.__atsSample.chartsReady` (both charts fired `arcgisRenderingComplete`), checks there are 2 charts, and turns dark mode on (the panel must no longer be white) and off again.

## Data note

ACS values are estimates with margins of error (the layer has a `_M` field next to each `_E` field). A county's median is not an average of anything, so the histogram shows how county medians are spread; it is not the income of the people in view.

## Links

- arcgis-chart: https://developers.arcgis.com/javascript/latest/references/charts-components/components/arcgis-chart/
- arcgis-charts-action-bar: https://developers.arcgis.com/javascript/latest/references/charts-components/components/arcgis-charts-action-bar/
- createModel: https://developers.arcgis.com/javascript/latest/references/charts-components/model/shared/setup-utils/
- Chart types: https://developers.arcgis.com/javascript/latest/charts/chart-types/
- Histogram: https://developers.arcgis.com/javascript/latest/charts/chart-types/histogram/
- Bar chart: https://developers.arcgis.com/javascript/latest/charts/chart-types/bar-chart/
- Tutorial, chart and map interactions: https://developers.arcgis.com/javascript/latest/tutorials/chart-and-map-interactions/
- Styling and theming charts: https://developers.arcgis.com/javascript/latest/charts/features-and-capabilities/styling-and-theming/
- 5.2 release notes: https://developers.arcgis.com/javascript/latest/release-notes/
- Calcite colors and modes: https://developers.arcgis.com/calcite-design-system/foundations/colors/
- Data item: https://www.arcgis.com/home/item.html?id=c9faa265b82848498bc0a8390c0afa65

## License

MIT, see the repository LICENSE. Census data from the U.S. Census Bureau ACS, in a layer published by Esri (Living Atlas).
