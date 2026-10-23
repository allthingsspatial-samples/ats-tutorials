import "@arcgis/core/assets/esri/themes/light/main.css";
import Map from "@arcgis/core/Map.js";
import MapView from "@arcgis/core/views/MapView.js";

// "topo-vector" is a 2D (legacy) basemap id. It loads with no API key,
// so this sample sets no esriConfig.apiKey and needs no .env file.
const map = new Map({ basemap: "topo-vector" });

const view = new MapView({
  container: "viewDiv",
  map,
  center: [-98.5, 39.8], // lon, lat: the contiguous United States
  zoom: 4,
});

// The CI smoke test waits for window.view.ready (see the repo README).
window.view = view;

view.when(() => console.log("Map view is ready"));
