import "@esri/calcite-components/components/calcite-shell";
import "@esri/calcite-components/components/calcite-shell-panel";
import "@esri/calcite-components/components/calcite-navigation";
import "@esri/calcite-components/components/calcite-navigation-logo";
import "@esri/calcite-components/components/calcite-label";
import "@esri/calcite-components/components/calcite-switch";
import "@esri/calcite-components/components/calcite-panel";
import "@esri/calcite-components/components/calcite-list";
import "@esri/calcite-components/components/calcite-list-item";
import "@esri/calcite-components/components/calcite-notice";
import "@esri/calcite-components/components/calcite-action";
import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-popup";
import "@arcgis/map-components/components/arcgis-zoom";
import "@arcgis/map-components/components/arcgis-feature";
import FeatureLayer from "@arcgis/core/layers/FeatureLayer.js";
import * as reactiveUtils from "@arcgis/core/core/reactiveUtils.js";
import { createPopupTemplate } from "./popup-template.js";

// Esri Living Atlas: "ACS Housing Units by Year Built (Latest)", item 204f0ea4315640fca8c2e0fbefe11a96.
// U.S. Census Bureau American Community Survey 5-year estimates. Public, no key.
const SERVICE_URL =
  "https://P3ePLMYs2RVChkJx.svcs.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/ACS_Housing_Units_by_Year_Built_View_Boundaries/FeatureServer";

const mapElement = document.querySelector("arcgis-map");
const popupElement = document.querySelector("arcgis-popup");
const endPanel = document.querySelector("#end-panel");
const results = document.querySelector("#results");
const feature = document.querySelector("#feature");
const hint = document.querySelector("#hint");
const panelSwitch = document.querySelector("#panel-mode");

await mapElement.viewOnReady();

// Dock the popup at the top right on every screen size, with no undock button.
// In 5.2.7 the dock-enabled attribute alone does not stay set once the map is ready, so set the property here too.
popupElement.dockOptions = { buttonEnabled: false, breakpoint: false, position: "top-right" };
popupElement.dockEnabled = true;

const counties = new FeatureLayer({
  url: `${SERVICE_URL}/1`,
  title: "Counties",
  // A little transparency lets the state lines below show through.
  opacity: 0.85,
  // The service hides counties at small scales; show them at every scale here.
  minScale: 0,
  maxScale: 0,
  popupTemplate: createPopupTemplate("{NAME}, {State}", ["NAME", "State"]),
  // Color by median year built: older is darker.
  renderer: {
    type: "simple",
    symbol: { type: "simple-fill", color: [200, 200, 200], outline: { color: [255, 255, 255, 0.5], width: 0.3 } },
    visualVariables: [
      {
        type: "color",
        field: "B25035_001E",
        legendOptions: { title: "Median year built" },
        stops: [
          { value: 1950, color: "#4a1486", label: "1950 or earlier" },
          { value: 1970, color: "#807dba" },
          { value: 1990, color: "#bcbddc" },
          { value: 2005, color: "#f2f0f7", label: "2005 or later" },
        ],
      },
    ],
  },
});
const states = new FeatureLayer({
  url: `${SERVICE_URL}/0`,
  title: "States",
  minScale: 0,
  maxScale: 0,
  popupTemplate: createPopupTemplate("{NAME}", ["NAME"]),
  renderer: {
    type: "simple",
    symbol: { type: "simple-fill", color: [0, 0, 0, 0], outline: { color: [30, 30, 30, 1], width: 1.5 } },
  },
});
// States go below the counties, so a click lists (and the popup shows) the county first.
mapElement.map.addMany([states, counties]);

// ---- The popup component (beta): a slotted "Zoom to" action. ----
document.querySelector("#zoom-action").addEventListener("click", () => {
  const selected = popupElement.selectedFeature;
  if (selected) mapElement.goTo(selected);
});

// ---- Panel mode: fetchPopupFeatures (5.1) instead of the popup. ----
let panelMode = false;
let lastFeatures = [];

function setPanelMode(on) {
  panelMode = on;
  panelSwitch.checked = on;
  // popupDisabled stops the popup opening on click; fetchPopupFeatures still works.
  mapElement.popupDisabled = on;
  if (on) mapElement.closePopup();
  endPanel.collapsed = !on;
}
panelSwitch.addEventListener("calciteSwitchChange", () => setPanelMode(panelSwitch.checked));

function showFeature(graphic) {
  // arcgis-feature renders the same PopupTemplate (text, Arcade, chart) outside the map.
  feature.graphic = graphic;
}

async function listFeaturesAt(screenPoint, pointerType) {
  // The component version returns a promise of an async generator: await it, then for await.
  const generator = await mapElement.fetchPopupFeatures(screenPoint, { pointerType });
  const features = [];
  results.replaceChildren();
  for await (const graphic of generator) {
    features.push(graphic);
    const item = document.createElement("calcite-list-item");
    item.label = graphic.attributes.State ? `${graphic.attributes.NAME}, ${graphic.attributes.State}` : graphic.attributes.NAME;
    item.description = `${graphic.layer.title}: ${graphic.attributes.B25034_001E.toLocaleString("en-US")} housing units, median year built ${graphic.attributes.B25035_001E}`;
    item.value = String(features.length - 1);
    results.append(item);
  }
  lastFeatures = features;
  hint.open = features.length === 0;
  if (features.length) {
    results.querySelector("calcite-list-item").selected = true;
    showFeature(features[0]);
  } else {
    feature.graphic = null;
  }
  return features;
}
results.addEventListener("calciteListChange", () => {
  const item = results.selectedItems[0];
  if (item) showFeature(lastFeatures[Number(item.value)]);
});

mapElement.addEventListener("arcgisViewClick", (event) => {
  if (!panelMode) return;
  listFeaturesAt({ x: event.detail.x, y: event.detail.y }, event.detail.pointerType);
});

// ---- In-page self-test, used by the smoke run: logs console.error only on failure. ----
async function selfTest() {
  const problems = [];
  const template = counties.popupTemplate;
  if (template.expressionInfos.length < 3) problems.push(`expressionInfos: ${template.expressionInfos.length}`);
  if (!template.content.some((c) => c.type === "media")) problems.push("no media content");
  if (!template.content.some((c) => c.type === "expression")) problems.push("no expression content");
  setPanelMode(true);
  await mapElement.whenLayerView(counties);
  await new Promise((r) => setTimeout(r, 500));
  await reactiveUtils.whenOnce(() => !mapElement.view.updating);
  const center = mapElement.view.toScreen(mapElement.view.center);
  const found = await listFeaturesAt(center, "mouse");
  if (found.length < 1) problems.push(`fetchPopupFeatures at the center found ${found.length} features`);
  setPanelMode(false);
  // Opening and closing the panel resizes the map: let it finish loading before the next step.
  await new Promise((r) => setTimeout(r, 500));
  await reactiveUtils.whenOnce(() => !mapElement.view.updating);
  for (const p of problems) console.error(`self-test: ${p}`);
  return { problems, found: found.map((g) => `${g.layer.title}: ${g.attributes.NAME}`) };
}

// For the smoke test and the tutorial's capture rig.
window.view = mapElement.view;
window.__atsSample = { counties, states, setPanelMode, listFeaturesAt, selfTest };
