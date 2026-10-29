import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-legend";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";
import ClassBreaksRenderer from "@arcgis/core/renderers/ClassBreaksRenderer.js";
import classBreaks from "@arcgis/core/smartMapping/statistics/classBreaks.js";
import { whenOnce } from "@arcgis/core/core/reactiveUtils.js";

const mapElement = document.querySelector("arcgis-map");
await mapElement.viewOnReady();
const view = mapElement.view;

const WHAT = {
  "natural-breaks": "Natural breaks: classes where the data has gaps, so similar counties stay together. Good for uneven data like this.",
  quantile: "Quantile: the same number of counties in each class. Every color covers the map equally, even when values are close.",
  "equal-interval": "Equal interval: every class has the same width. With a few very dense metro counties, almost all of Texas lands in class 1.",
  "standard-deviation": "Standard deviation: classes 1 standard deviation wide, the middle one centered on the mean, so the data sets the number of classes, not the picker. On skewed data the classes below the mean fall under zero, so they are dropped.",
};

// A yellow-to-purple sequential ramp, sampled to the number of classes (up to 9).
const RAMP = ["#fff5b8", "#fee391", "#fec44f", "#fd9a44", "#f46d43", "#d73f5f", "#b02a6e", "#7f1f73", "#4a1466"];
const rampColors = (n) => Array.from({ length: n }, (_, i) => RAMP[Math.round((i * (RAMP.length - 1)) / Math.max(n - 1, 1))]);

const counties = new GeoJSONLayer({
  url: new URL("data/texas-counties.geojson", location.href).href,
  title: "Texas counties",
  copyright: "US Census Bureau",
  popupTemplate: { title: "{NAME} County", content: "People per km²: {DENSITY}<br>Population 2024: {POP2024}" },
});
mapElement.map.add(counties);

// The layer is client-side, so classBreaks() uses the features in the view: show the whole state first.
const layerView = await view.whenLayerView(counties);
await view.goTo(counties.fullExtent.expand(1.05), { animate: false });
await whenOnce(() => !layerView.updating);

const state = { method: "natural-breaks", numClasses: 5 };

async function update() {
  const result = await classBreaks({
    layer: counties,
    view,
    useFeaturesInView: true,
    field: "DENSITY",
    classificationMethod: state.method,
    numClasses: state.numClasses,
    standardDeviationInterval: 1,
  });
  // Standard deviation steps out symmetrically from the mean; keep only classes that hold data.
  const dataMin = result.minValue ?? result.classBreakInfos[0].minValue;
  const classBreakInfos = result.classBreakInfos
    .filter((info) => info.maxValue > dataMin)
    .map((info) => ({ minValue: Math.max(info.minValue, dataMin), maxValue: info.maxValue }));
  const colors = rampColors(classBreakInfos.length);
  counties.renderer = new ClassBreaksRenderer({
    field: "DENSITY",
    legendOptions: { title: "People per km²" },
    classBreakInfos: classBreakInfos.map((info, i) => ({
      minValue: info.minValue,
      maxValue: info.maxValue,
      label: `${info.minValue.toFixed(2)} - ${info.maxValue.toFixed(2)}`,
      symbol: { type: "simple-fill", color: colors[i], outline: { color: [255, 255, 255, 0.6], width: 0.4 } },
    })),
  });
  document.querySelector("#what").textContent = `${WHAT[state.method]} (${classBreakInfos.length} classes)`;
  for (const button of document.querySelectorAll("#classes button")) {
    button.setAttribute("aria-pressed", String(Number(button.textContent) === state.numClasses));
    button.disabled = state.method === "standard-deviation";
  }
}

document.querySelector("#method").addEventListener("change", (event) => {
  state.method = event.target.value;
  update();
});
for (const button of document.querySelectorAll("#classes button")) {
  button.addEventListener("click", () => {
    state.numClasses = Number(button.textContent);
    update();
  });
}
await update();

// The CI smoke test waits for window.view.ready (see the repo README).
window.view = view;
