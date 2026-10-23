import "@arcgis/core/assets/esri/themes/dark/main.css";
import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-swipe";
import Map from "@arcgis/core/Map.js";
import ImageryLayer from "@arcgis/core/layers/ImageryLayer.js";

// Esri's public multispectral Landsat image service (Landsat 8 and 9,
// plus the Global Land Survey epochs). No API key is needed to read it.
const LANDSAT_URL =
  "https://landsat.arcgis.com/arcgis/rest/services/Landsat/MS/ImageServer";

// One layer per date. The definition expression keeps a single scene,
// picked by its Name in the service's catalog.
function landsatScene(name) {
  return new ImageryLayer({
    url: LANDSAT_URL,
    definitionExpression: `Name = '${name}'`,
    // A raster function published with the service: true color, stretched.
    rasterFunction: { functionName: "Natural Color with DRA" },
  });
}

// Lake Mead, Nevada and Arizona: two clear scenes, 22 years apart.
const before = landsatScene("p039r035_7dt20000503_z11_MS"); // Landsat 7, 3 May 2000
const after = landsatScene("LC09_L1TP_039035_20220703_20230407_02_T1"); // Landsat 9, 3 July 2022

const mapElement = document.querySelector("arcgis-map");
// "dark-gray-vector" is a 2D (legacy) basemap id. It gives the view its zoom
// levels, and this sample sets no esriConfig.apiKey.
mapElement.map = new Map({ basemap: "dark-gray-vector", layers: [before, after] });

// Before on the left (start), after on the right (end).
const swipe = document.querySelector("arcgis-swipe");
await swipe.componentOnReady();
swipe.startLayers.add(before);
swipe.endLayers.add(after);

// The CI smoke test waits for window.view.ready (see the repo README).
await mapElement.viewOnReady();
window.view = mapElement.view;
