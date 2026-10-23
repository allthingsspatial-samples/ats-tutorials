import "@arcgis/map-components/components/arcgis-map";

const mapElement = document.querySelector("arcgis-map");
await mapElement.viewOnReady();

// Keep the map near the canyon: no zooming out past level 9.
mapElement.constraints = { minZoom: 9 };

// Remember where the map started, for the Home button.
const home = mapElement.viewpoint.clone();

const zoomInButton = document.querySelector("#zoom-in");
const zoomOutButton = document.querySelector("#zoom-out");

// Each button calls the map component directly. No widget, no view model.
zoomInButton.addEventListener("click", () => mapElement.zoomIn());
zoomOutButton.addEventListener("click", () => mapElement.zoomOut());
document.querySelector("#home").addEventListener("click", () => mapElement.goTo(home));

// Two basemaps, one button.
const basemaps = ["satellite", "topo-vector"];
let current = 0;
document.querySelector("#basemap").addEventListener("click", () => {
  current = (current + 1) % basemaps.length;
  mapElement.basemap = basemaps[current];
});

// Grey out a zoom button when the map cannot zoom any further that way.
function updateZoomButtons() {
  zoomInButton.disabled = !mapElement.canZoomIn;
  zoomOutButton.disabled = !mapElement.canZoomOut;
}
mapElement.addEventListener("arcgisViewChange", updateZoomButtons);
updateZoomButtons();

// The CI smoke test waits for window.view.ready (see the repo README).
window.view = mapElement.view;
