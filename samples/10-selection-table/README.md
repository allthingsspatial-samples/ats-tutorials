# 10 Select Features, Show a Table, Export to CSV

Draw a rectangle or a lasso on the map with the Selection Toolbar, see what you picked in a Selection List and a Feature Table that stay in sync, and download exactly those rows as a CSV file. No hand-written selection or CSV code: the three components share the map's selection manager, and the export is built into the Feature Table. It goes with the ATS Build episode BLD-S02E06, "Select Features, Table, CSV Export in ArcGIS JS 5.2".

- Data: "Recent Earthquakes" from Esri's Living Atlas (item 9e2f2b544c954fda9cd13b7f3e6eebce, layer https://services9.arcgis.com/RHVPKKiFTONKtxq3/arcgis/rest/services/USGS_Seismic_Data_v1/FeatureServer/0). The item page says events are updated as often as every 5 minutes and kept up to 30 days, except: magnitude below 4.5 for 7 days, significance ("sig") 600 or more for 90 days. Source: USGS Earthquake Hazards Program. Public, no sign-in. The layer changes through the day, so your counts will differ from the episode.
- SDK: `@arcgis/core` and `@arcgis/map-components` 5.2.7, `@esri/calcite-components` 5.2.1 (the version map-components 5.2.7 asks for). All pinned exactly. No API key.
- Build tool: Vite

```bash
npm ci
npm run dev
```

## The three components

| Component | Since | Job |
|---|---|---|
| `arcgis-selection-toolbar` | 5.2 | pan, point, rectangle, lasso and polygon tools; add / remove / replace; a count chip that clears the selection |
| `arcgis-selection-list` | 5.2 | what is selected, grouped by layer; remove one feature or one layer, zoom to it |
| `arcgis-feature-table` | (table) 4.x; `mapLayerId` 5.1 | the rows, with the selected ones checked |

All three work on the map's selection manager (`arcgisMap.selectionManager`, labelled beta on the map component). The toolbar sits in the map's `top-start` slot; the list and the table sit in Calcite shell panels and find the map through `reference-element="map"`.

## Selection Toolbar

The toolbar finds the selectable layers in the view by itself; nothing to configure for a layer added to the map. Its tools add to, remove from or replace the selection (the dropdown at its start). With the lasso, drag a loop around the features and double-click to finish it: in 5.2.7 the lasso is the polygon tool in hybrid mode, so the drag alone leaves the shape open and selects nothing yet. The same selection can be set in code:

```js
mapElement.selectionManager.replace(quakes, [objectId1, objectId2, objectId3]);
```

## Feature Table: `mapLayerId` and `sync-view-selection`

`mapLayerId` (since 5.1) binds the table to a layer that is already in the map, by the layer's `id`, instead of passing the layer object. In 5.2 the table also has `layerId`, `tableId` (with `layerItemId`) and `viewTimeEnabled`.

In this sample the layer is created in code after the page loads, so `main.js` sets `table.mapLayerId = quakes.id` right after adding the layer. A `map-layer-id` attribute in the HTML is read before that layer exists and leaves the table empty (tested with 5.2.7). With a web map, whose layers exist when the map loads, the attribute works in the HTML.

`sync-view-selection` makes the table read and write the map's selection manager, so rows selected on the map are checked in the table and the other way round. The "Selected only" switch sets `filterBySelectionEnabled`.

## CSV export (built in)

The table's menu has "Export selection to CSV". The sample's "Download CSV" button calls the same thing:

```js
table.exportSelectionToCSV(true); // true = add the point geometry as lon / lat columns
```

Limits, from the API reference: it exports selected rows only; geometry is exported only for point features; multipart geometries are not supported. The columns are the layer's fields (the ones the layer fetched with `outFields`), not the table's column template. In Chrome and Edge the browser opens a "Save as" dialog (the export uses the File System Access save picker); the suggested file name is the layer title.

Checked for this sample: a rectangle drag over California selected 367 earthquakes; the table showed 367 selected rows and the exported file had a header plus 367 rows, ending in `lon,lat`.

## Smoke test

`smoke.checks.mjs` checks the three components are defined and runs the in-page self-test (`window.__atsSample.selfTest()`): it selects the three strongest quakes in code, expects a selection count of 3 and 3 highlighted table rows, then clears the selection. The self-test logs `console.error` only on failure, so the standard smoke run fails with it. The save dialog cannot run headless, so the CSV download is checked in a local browser run, not in CI.

## Links

- Selection Toolbar: https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-selection-toolbar/
- Selection List: https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-selection-list/
- Feature Table component (`mapLayerId`, `syncViewSelection`, `exportSelectionToCSV`): https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-feature-table/
- FeatureTable export limits: https://developers.arcgis.com/javascript/latest/references/core/widgets/FeatureTable/
- SelectionManager: https://developers.arcgis.com/javascript/latest/references/core/views/SelectionManager/
- 5.2 release notes (Selection map components): https://developers.arcgis.com/javascript/latest/release-notes/
- 5.1 release notes (`mapLayerId`): https://archive.developers.arcgis.com/javascript/v5-1/release-notes/
- USGS earthquake feeds: https://earthquake.usgs.gov/earthquakes/feed/

## License

MIT, see the repository LICENSE. Earthquake data from the U.S. Geological Survey (public domain), served through Esri's Living Atlas.
