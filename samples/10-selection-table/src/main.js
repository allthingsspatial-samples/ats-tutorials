import "@esri/calcite-components/components/calcite-shell";
import "@esri/calcite-components/components/calcite-shell-panel";
import "@esri/calcite-components/components/calcite-navigation";
import "@esri/calcite-components/components/calcite-navigation-logo";
import "@esri/calcite-components/components/calcite-panel";
import "@esri/calcite-components/components/calcite-label";
import "@esri/calcite-components/components/calcite-switch";
import "@esri/calcite-components/components/calcite-button";
import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-zoom";
import "@arcgis/map-components/components/arcgis-selection-toolbar";
import "@arcgis/map-components/components/arcgis-selection-list";
import "@arcgis/map-components/components/arcgis-feature-table";
import FeatureLayer from "@arcgis/core/layers/FeatureLayer.js";
import * as reactiveUtils from "@arcgis/core/core/reactiveUtils.js";

// Esri Living Atlas "Recent Earthquakes" (item 9e2f2b544c954fda9cd13b7f3e6eebce): USGS events, updated as often as
// every 5 minutes. Most events stay up to 30 days; below magnitude 4.5, 7 days. Public, no key.
const QUAKES_URL = "https://services9.arcgis.com/RHVPKKiFTONKtxq3/arcgis/rest/services/USGS_Seismic_Data_v1/FeatureServer/0";

const mapElement = document.querySelector("arcgis-map");
const table = document.querySelector("#table");
const downloadButton = document.querySelector("#download");
const selectedOnly = document.querySelector("#selected-only");

await mapElement.viewOnReady();

// The layer id is what the table's map-layer-id points at.
const quakes = new FeatureLayer({
  id: "quakes",
  url: QUAKES_URL,
  title: "Earthquakes",
  // The Selection List names each feature by the display field.
  displayField: "place",
  outFields: ["mag", "place", "eventTime", "depth", "magType", "url"],
  renderer: {
    type: "simple",
    symbol: { type: "simple-marker", color: [255, 122, 69, 0.8], outline: { color: [255, 255, 255, 0.7], width: 0.5 } },
    visualVariables: [{ type: "size", field: "mag", stops: [{ value: 1, size: 4 }, { value: 7, size: 28 }] }],
  },
  popupEnabled: false,
});
mapElement.map.add(quakes);
// Bind the table to that map layer by its id. The layer is added in code after the table is
// on the page, so set mapLayerId now (a map-layer-id attribute in the HTML is read before
// this layer exists and finds nothing). With a web map, map-layer-id can go in the HTML.
table.mapLayerId = quakes.id;

// The table shows these columns, in this order.
table.tableTemplate = {
  columnTemplates: [
    { type: "field", fieldName: "mag", label: "Magnitude" },
    { type: "field", fieldName: "place", label: "Place" },
    { type: "field", fieldName: "eventTime", label: "Time" },
    { type: "field", fieldName: "depth", label: "Depth (km)" },
    { type: "field", fieldName: "magType", label: "Magnitude type" },
  ],
};

// The map's selection manager is shared by the toolbar, the list and the table (sync-view-selection).
const selectionManager = mapElement.selectionManager;

// "Selected only": show just the selected rows.
selectedOnly.addEventListener("calciteSwitchChange", () => {
  table.filterBySelectionEnabled = selectedOnly.checked;
});

// The built-in export writes the selected rows. true = add the point geometry as columns.
reactiveUtils.watch(
  () => selectionManager.count,
  (count) => {
    downloadButton.disabled = count === 0;
    downloadButton.textContent = count ? `Download CSV (${count})` : "Download CSV";
  },
  { initial: true },
);
downloadButton.addEventListener("click", () => table.exportSelectionToCSV(true));

// ---- In-page self-test, used by the smoke run: logs console.error only on failure. ----
async function selfTest() {
  const problems = [];
  await mapElement.whenLayerView(quakes);
  await reactiveUtils.whenOnce(() => table.layer === quakes);
  // Three known features: the three strongest quakes in the layer right now.
  const { features } = await quakes.queryFeatures({ where: "1=1", outFields: ["OBJECTID"], orderByFields: ["mag DESC"], num: 3 });
  const ids = features.map((f) => f.attributes.OBJECTID);
  selectionManager.replace(quakes, ids);
  await new Promise((r) => setTimeout(r, 500));
  const managerCount = selectionManager.count;
  const tableCount = table.highlightIds.length;
  if (managerCount !== 3) problems.push(`selection manager count ${managerCount}, expected 3`);
  if (tableCount !== 3) problems.push(`table highlightIds ${tableCount}, expected 3`);
  if (downloadButton.disabled) problems.push("download button still disabled with a selection");
  selectionManager.clear();
  await new Promise((r) => setTimeout(r, 300));
  if (table.highlightIds.length !== 0) problems.push(`table kept ${table.highlightIds.length} highlights after clear`);
  for (const p of problems) console.error(`self-test: ${p}`);
  return { problems, ids, managerCount, tableCount };
}

// For the smoke test and the tutorial's capture rig.
window.view = mapElement.view;
window.__atsSample = { quakes, table, selectionManager, selfTest };
