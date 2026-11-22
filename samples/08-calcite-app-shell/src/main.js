// Calcite components used by the layout in index.html.
import "@esri/calcite-components/components/calcite-shell";
import "@esri/calcite-components/components/calcite-shell-panel";
import "@esri/calcite-components/components/calcite-navigation";
import "@esri/calcite-components/components/calcite-navigation-logo";
import "@esri/calcite-components/components/calcite-action-bar";
import "@esri/calcite-components/components/calcite-action";
import "@esri/calcite-components/components/calcite-panel";
// Map components that live inside the panels.
import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-layer-list";
import "@arcgis/map-components/components/arcgis-legend";
import "@arcgis/map-components/components/arcgis-feature";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";

// USGS summary feed: every earthquake of magnitude 2.5 or more in the past 7 days.
const FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson";

const mapElement = document.querySelector("arcgis-map");
const startPanel = document.querySelector("#start-panel");
const endPanel = document.querySelector("#end-panel");
const feature = document.querySelector("#feature");
const actions = [...document.querySelectorAll("calcite-action[data-panel]")];
const panels = [...document.querySelectorAll("calcite-panel[data-panel]")];

// ---- Action bar: one action opens its panel; the same action again closes it. ----
let openName = null;
function open(name) {
  openName = name;
  for (const action of actions) action.active = action.dataset.panel === name;
  // hidden removes a panel from the layout; closed would only hide it and keep its space.
  for (const panel of panels) {
    panel.hidden = panel.dataset.panel !== name;
    panel.closed = false;
  }
  startPanel.collapsed = name === null;
}
for (const action of actions) {
  action.addEventListener("click", () => open(openName === action.dataset.panel ? null : action.dataset.panel));
}
// The panel's own close button closes it the same way.
for (const panel of panels) panel.addEventListener("calcitePanelClose", () => open(null));
open("layers");

// ---- Dark mode: set color-scheme on :root (Calcite 5.2); remember the choice. ----
const themeAction = document.querySelector("#theme");
function setTheme(theme) {
  document.documentElement.style.colorScheme = theme;
  // The basemap is map content, not UI: swap it to match.
  mapElement.basemap = theme === "dark" ? "dark-gray-vector" : "gray-vector";
  themeAction.icon = theme === "dark" ? "brightness" : "moon";
  themeAction.text = theme === "dark" ? "Light mode" : "Dark mode";
  localStorage.setItem("ats-08-theme", theme);
}
themeAction.addEventListener("click", () =>
  setTheme(getComputedStyle(document.documentElement).colorScheme === "dark" ? "light" : "dark"),
);
setTheme(localStorage.getItem("ats-08-theme") === "dark" ? "dark" : "light");

// ---- Responsive: under 700 px wide, panels float over the map and start collapsed. ----
const narrow = window.matchMedia("(max-width: 700px)");
function fit() {
  const mode = narrow.matches ? "overlay" : "dock";
  startPanel.displayMode = mode;
  endPanel.displayMode = mode;
  if (narrow.matches) open(null);
}
narrow.addEventListener("change", fit);
fit();

// ---- Map: the earthquake layer and click -> details. ----
await mapElement.viewOnReady();
const quakes = new GeoJSONLayer({
  url: FEED_URL,
  title: "Earthquakes M2.5+ (past 7 days)",
  copyright: "USGS",
  // "time" is milliseconds since 1970: declare it as a date field.
  fields: [
    { name: "mag", type: "double", alias: "Magnitude" },
    { name: "place", type: "string", alias: "Place" },
    { name: "time", type: "date", alias: "Time" },
  ],
  orderBy: [{ field: "mag", order: "ascending" }],
  renderer: {
    type: "simple",
    symbol: { type: "simple-marker", color: [255, 122, 69, 0.75], outline: { color: [255, 255, 255, 0.6], width: 0.5 } },
    visualVariables: [{ type: "size", field: "mag", stops: [{ value: 2.5, size: 4 }, { value: 7, size: 30 }] }],
  },
  popupTemplate: {
    title: "Magnitude {mag}",
    content: [{ type: "fields", fieldInfos: [
      { fieldName: "place", label: "Place" },
      { fieldName: "time", label: "Time", format: { dateFormat: "short-date-short-time" } },
    ] }],
  },
});
mapElement.map.add(quakes);
// Clicks fill the end panel instead of opening a popup.
mapElement.popupDisabled = true;

const total = await quakes.queryFeatureCount();
document.querySelector("#count").textContent = `${total.toLocaleString("en-US")} earthquakes in the feed right now.`;

mapElement.addEventListener("arcgisViewClick", async (event) => {
  const { results } = await mapElement.hitTest(event.detail, { include: quakes });
  // Several quakes can overlap: show the strongest one under the cursor.
  const graphic = results
    .map((result) => result.graphic)
    .sort((a, b) => b.attributes.mag - a.attributes.mag)[0];
  feature.graphic = graphic ?? null;
  endPanel.collapsed = !graphic;
});
document.querySelector("#details-panel").addEventListener("calcitePanelClose", () => {
  endPanel.collapsed = true;
  document.querySelector("#details-panel").closed = false;
});

// For the smoke test and the tutorial's capture rig.
window.view = mapElement.view;
window.__atsSample = { open, setTheme, quakes, total };
