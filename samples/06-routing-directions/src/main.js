// Calcite components used by the layout in index.html.
import "@esri/calcite-components/components/calcite-shell";
import "@esri/calcite-components/components/calcite-shell-panel";
import "@esri/calcite-components/components/calcite-navigation";
import "@esri/calcite-components/components/calcite-navigation-logo";
import "@esri/calcite-components/components/calcite-panel";
import "@esri/calcite-components/components/calcite-notice";
// Map components.
import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-directions";
import esriConfig from "@arcgis/core/config.js";

// Vite reads VITE_ARCGIS_TOKEN from .env.local (git-ignored) and inlines it at build time.
const apiKey = import.meta.env.VITE_ARCGIS_TOKEN?.trim() || "";
const mode = apiKey ? "key" : "no-key";

const mapElement = document.querySelector("arcgis-map");
const panel = document.querySelector("#directions-panel");

if (mode === "key") {
  // One key for the whole app: basemap, geocoding and routing requests all carry it.
  esriConfig.apiKey = apiKey;
  // The navigation basemap style needs the basemaps privilege.
  mapElement.basemap = "arcgis/navigation";

  const directions = document.createElement("arcgis-directions");
  directions.referenceElement = "map";
  // Creates a RouteLayer, adds it to the map and solves routes on the ArcGIS routing service.
  directions.useDefaultRouteLayer = true;
  directions.unit = "imperial";
  // This sample does not save routes to a portal.
  directions.hideSaveButton = true;
  directions.hideSaveAsButton = true;
  panel.append(directions);
} else {
  // No key: a basemap that needs no key, the notice, and no Directions component,
  // so no routing or geocoding request is ever sent without a key.
  mapElement.basemap = "gray-vector";
  document.querySelector("#no-key").open = true;
}

await mapElement.viewOnReady();

// For the smoke test and the tutorial's capture rig.
window.view = mapElement.view;
window.__atsSample = { mode };
