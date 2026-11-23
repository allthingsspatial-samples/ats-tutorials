import "@esri/calcite-components/components/calcite-shell";
import "@esri/calcite-components/components/calcite-shell-panel";
import "@esri/calcite-components/components/calcite-navigation";
import "@esri/calcite-components/components/calcite-navigation-logo";
import "@esri/calcite-components/components/calcite-panel";
import "@esri/calcite-components/components/calcite-label";
import "@esri/calcite-components/components/calcite-switch";
import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-zoom";
// One chart element for every chart type, plus the action bar that goes in its "action-bar" slot.
import "@arcgis/charts-components/components/arcgis-chart";
import "@arcgis/charts-components/components/arcgis-charts-action-bar";
import { createModel } from "@arcgis/charts-components/model/shared/setup-utils"; // npm export has no ".js" (the CDN docs path has one)
import FeatureLayer from "@arcgis/core/layers/FeatureLayer.js";
import WebMap from "@arcgis/core/WebMap.js";

// Esri Living Atlas "ACS Median Household Income (Latest)" (item c9faa265b82848498bc0a8390c0afa65), county layer.
// U.S. Census Bureau American Community Survey 5-year estimates; public, no key. "Latest" means Esri moves it to the
// newest ACS release, so the numbers change once a year (2020-2024 when this sample was written).
const COUNTIES_URL =
  "https://P3ePLMYs2RVChkJx.svcs.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/ACS_Median_Household_Income_View_Boundaries/FeatureServer/1";
const INCOME_FIELD = "B19049_001E"; // Median household income in the past 12 months (dollars)

// Optional: a public web map whose county layer has a chart saved on it (Map Viewer > Charts > Save).
// Leave empty to skip the third chart. LAYER_ID is that layer's id in the web map.
const WEBMAP_ID = "";
const LAYER_ID = "acs-counties";

const mapElement = document.querySelector("arcgis-map");
const histogram = document.querySelector("#histogram");
const barChart = document.querySelector("#bar-chart");
const savedChart = document.querySelector("#saved-chart");
const darkSwitch = document.querySelector("#dark-switch");

// 1. The map and the county layer. With a web map, the layer comes from the web map; without one, we add it.
let counties;
if (WEBMAP_ID) {
  mapElement.map = new WebMap({ portalItem: { id: WEBMAP_ID } });
  await mapElement.viewOnReady();
  counties = mapElement.map.findLayerById(LAYER_ID);
} else {
  mapElement.basemap = "gray-vector";
  await mapElement.viewOnReady();
  counties = new FeatureLayer({
    id: LAYER_ID,
    url: COUNTIES_URL,
    title: "Median household income",
    outFields: ["NAME", "State", INCOME_FIELD],
  });
  mapElement.map.add(counties);
}
mapElement.center = [-86.5, 37.5];
mapElement.zoom = 6;
await mapElement.viewOnReady();
await mapElement.whenLayerView(counties);

// For the smoke test and the walkthrough: chartsReady turns true once both charts have drawn.
window.__atsSample = { chartsReady: false };
const drawn = new Set();
for (const chart of [histogram, barChart]) {
  chart.addEventListener("arcgisRenderingComplete", () => {
    drawn.add(chart.id);
    window.__atsSample.chartsReady = drawn.size === 2;
  });
}

// 2. Histogram: one model, made from the layer. The chart type comes from the model, not from the tag.
const histogramModel = await createModel({ layer: counties, chartType: "histogram" });
histogramModel.numericField = INCOME_FIELD;
histogramModel.binCount = 32; // the default; a histogram can have up to 64 bins
histogramModel.titleText = "Median household income (counties in view)";
histogramModel.xAxisTitleText = "Median household income (dollars)";
histogram.model = histogramModel;

// 3. Bar chart: a second chart element with a bar chart model. One bar per state, counting counties.
const barModel = await createModel({ layer: counties, chartType: "barChart" });
barModel.xAxisField = "State";
barModel.rotated = true; // horizontal bars: state names stay readable
barModel.setSortOrder("yAxisDesc"); // most counties first
barModel.titleText = "Counties in view, by state";
barChart.model = barModel;

// 4. 5.2 reference element: the chart saved in the web map loads from map-layer-id + chart-index. No model in code.
if (WEBMAP_ID) {
  savedChart.mapLayerId = LAYER_ID;
  savedChart.parentElement.hidden = false;
} else {
  savedChart.parentElement.remove(); // no web map, no saved chart
}

// 5. Dark mode: one CSS property, color-scheme, on the html element. Calcite and the charts both follow it.
//    The basemap is map content, not UI, so it is swapped too.
function setDark(dark) {
  document.documentElement.style.colorScheme = dark ? "dark" : "light";
  if (!WEBMAP_ID) mapElement.basemap = dark ? "dark-gray-vector" : "gray-vector";
}
darkSwitch.addEventListener("calciteSwitchChange", () => setDark(darkSwitch.checked));
window.view = mapElement.view;
Object.assign(window.__atsSample, { counties, histogramModel, barModel, setDark });
