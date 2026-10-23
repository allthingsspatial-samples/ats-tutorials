import "@arcgis/core/assets/esri/themes/dark/main.css";
import "@arcgis/map-components/components/arcgis-map";
import Map from "@arcgis/core/Map.js";
import ImageryLayer from "@arcgis/core/layers/ImageryLayer.js";
import GraphicsLayer from "@arcgis/core/layers/GraphicsLayer.js";
import SketchViewModel from "@arcgis/core/widgets/Sketch/SketchViewModel.js";
import esriRequest from "@arcgis/core/request.js";

// The USGS 3D Elevation Program (3DEP) bare-earth DEM image service.
// It is public: no API key and no sign-in.
const DEM_URL =
  "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer";

// One pixel per 10 map units (Web Mercator meters) in the downloaded file.
const CELL_SIZE = 10;

// Show the elevation as a hillshade, one of the service's raster functions.
const dem = new ImageryLayer({
  url: DEM_URL,
  rasterFunction: { functionName: "Hillshade Elevation Tinted" },
});
const boxes = new GraphicsLayer();

const mapElement = document.querySelector("arcgis-map");
mapElement.map = new Map({ basemap: "topo-vector", layers: [dem, boxes] });
await mapElement.viewOnReady();
const view = mapElement.view;

const status = document.querySelector("#status");
const sketch = new SketchViewModel({ view, layer: boxes });

document.querySelector("#draw").addEventListener("click", () => {
  boxes.removeAll();
  sketch.create("rectangle");
  status.textContent = "Drag on the map to draw the box.";
});

sketch.on("create", async (event) => {
  if (event.state !== "complete") return;
  const extent = event.graphic.geometry.extent;
  const width = Math.round(extent.width / CELL_SIZE);
  const height = Math.round(extent.height / CELL_SIZE);

  // The service refuses images larger than its published limit.
  if (width > dem.imageMaxWidth || height > dem.imageMaxHeight) {
    status.textContent = `Box too large: ${width} x ${height} pixels. The limit is ${dem.imageMaxWidth} x ${dem.imageMaxHeight}.`;
    return;
  }

  status.textContent = `Clipping ${width} x ${height} pixels...`;
  // exportImage cuts the box out of the service. With no raster function,
  // the pixels are elevation values, as 32-bit floats.
  let response;
  try {
    response = await esriRequest(`${DEM_URL}/exportImage`, {
      query: {
        bbox: [extent.xmin, extent.ymin, extent.xmax, extent.ymax].join(","),
        bboxSR: 3857,
        imageSR: 3857,
        size: `${width},${height}`,
        format: "tiff",
        pixelType: "F32",
        f: "image",
      },
      responseType: "blob",
    });
  } catch (error) {
    status.textContent = `The export failed: ${error.message}`;
    return;
  }

  // Save the GeoTIFF in the browser. No server of our own is involved.
  const link = document.createElement("a");
  link.href = URL.createObjectURL(response.data);
  link.download = "3dep-clip.tif";
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  status.textContent = `Saved 3dep-clip.tif: ${width} x ${height} pixels, ${(response.data.size / 1e6).toFixed(1)} MB.`;
});

// The CI smoke test waits for window.view.ready (see the repo README).
window.view = view;
