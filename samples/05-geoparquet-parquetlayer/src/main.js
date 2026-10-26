import "@arcgis/map-components/components/arcgis-map";
import ParquetLayer from "@arcgis/core/layers/ParquetLayer.js";
import ParquetFilesData from "@arcgis/core/layers/support/ParquetFilesData.js";
import GeometryEncodingWkb from "@arcgis/core/layers/support/GeometryEncodingWkb.js";
import * as reactiveUtils from "@arcgis/core/core/reactiveUtils.js";

// The GeoParquet files this sample can load. Only the first one is in the repo;
// make the others with scripts/extract.py (see the README).
const FILES = {
  "denver-places.parquet": "Denver box",
  "colorado-places.parquet": "Colorado box (make with extract.py)",
  "four-corners-places.parquet": "Four Corners box (make with extract.py)",
};

const mapElement = document.querySelector("arcgis-map");
await mapElement.viewOnReady();
const view = mapElement.view;

// Color the points by their Overture category; everything else is grey.
const colors = {
  restaurant: "#ff6b6b", financial_service: "#60efff", home_service: "#ffbf0b",
  real_estate_service: "#b28dff", personal_or_beauty_service: "#ff9de6", automotive_service: "#7bd88f",
};
const dot = (color) => ({ type: "simple-marker", size: 3, color, outline: null });
const renderer = {
  type: "unique-value",
  field: "category",
  defaultSymbol: dot("#5b6b7f"),
  uniqueValueInfos: Object.entries(colors).map(([value, color]) => ({ value, symbol: dot(color) })),
};

let layer;
async function loadFile(name) {
  if (layer) mapElement.map.remove(layer);
  document.querySelector("#loaded").textContent = `Loading ${name}...`;
  document.querySelector("#hits").textContent = "Click the map: hitTest lists every place under the cursor.";
  const started = performance.now();

  // The file is GeoParquet: WKB points in WGS84. In our 5.1.27 tests the points only drew
  // once the encoding, spatial reference and geometry type were set here.
  layer = new ParquetLayer({
    data: new ParquetFilesData({ urls: [new URL(`data/${name}`, location.href).href] }),
    geometryEncoding: new GeometryEncodingWkb({ field: "geometry" }),
    spatialReference: { wkid: 4326 },
    geometryType: "point",
    renderer,
    definitionExpression: document.querySelector("#filter").value || null,
    popupEnabled: false,
  });
  mapElement.map.add(layer);
  // Wait until the layer view has drawn the file.
  const layerView = await view.whenLayerView(layer);
  await Promise.race([reactiveUtils.whenOnce(() => layerView.updating), new Promise((r) => setTimeout(r, 1000))]);
  await reactiveUtils.whenOnce(() => !layerView.updating);
  const total = await layer.queryFeatureCount({ where: "1=1" });
  const seconds = ((performance.now() - started) / 1000).toFixed(1);
  document.querySelector("#loaded").textContent = `${total.toLocaleString()} places loaded in ${seconds} s`;
  window.lastLoad = { name, total, seconds: Number(seconds) };
  await runQueries();
}

// Queries run against the layer's current definitionExpression.
let run = 0;
async function runQueries() {
  const mine = ++run;
  // Statistics queries take their own where clause, so add the layer's filter to it.
  const filter = layer.definitionExpression ? `(${layer.definitionExpression}) AND ` : "";
  const count = await layer.queryFeatureCount();
  document.querySelector("#count").textContent = `${count.toLocaleString()} places match`;

  // Statistics: count per category, largest first.
  const statistics = {
    where: `${filter}category IS NOT NULL`,
    outStatistics: [{ statisticType: "count", onStatisticField: "id", outStatisticFieldName: "n" }],
    groupByFieldsForStatistics: ["category"],
  };
  let rows;
  let note = "";
  try {
    rows = (await layer.queryFeatures({ ...statistics, orderByFields: ["n DESC"] })).features.map((f) => f.attributes);
  } catch (error) {
    // The docs list orderByFields for datasets of up to 500,000 features. Past that, sort in the browser.
    rows = (await layer.queryFeatures(statistics)).features.map((f) => f.attributes).sort((a, b) => b.n - a.n);
    note = `orderByFields refused (${error.message}); sorted in the browser`;
  }
  if (mine !== run) return; // a newer filter or file took over
  document.querySelector("#top").innerHTML = rows.slice(0, 5)
    .map((row) => `<li>${row.category}: ${row.n.toLocaleString()}</li>`).join("");
  document.querySelector("#note").textContent = note;

  // returnDistinctValues: how many different categories are in the file.
  const distinct = await layer.queryFeatures({
    where: `${filter}category IS NOT NULL`, outFields: ["category"], returnDistinctValues: true, returnGeometry: false,
  });
  document.querySelector("#distinct").textContent = `${distinct.features.length} distinct categories`;
  window.lastQueries = { count, top: rows.slice(0, 5), note, distinct: distinct.features.length };
}

// Filter on the layer itself: the map and the queries follow the expression.
document.querySelector("#filter").addEventListener("change", async (event) => {
  layer.definitionExpression = event.target.value || null;
  await runQueries();
});

// hitTest returns every place under the click, not only the top one.
view.on("click", async (event) => {
  const { results } = await view.hitTest(event, { include: [layer] });
  const objectIds = results.map((result) => result.graphic.getObjectId());
  // The hit graphics carry the object ID; ask the layer for their names.
  const named = objectIds.length
    ? (await layer.queryFeatures({ objectIds: objectIds.slice(0, 50), outFields: ["name"], returnGeometry: false })).features
    : [];
  const names = named.map((f) => f.attributes.name ?? "(no name)");
  document.querySelector("#hits").textContent =
    `${objectIds.length} places under the cursor: ${names.slice(0, 3).join(", ")}${objectIds.length > 3 ? ", ..." : ""}`;
  window.lastHits = { count: objectIds.length, names };
});

const fileSelect = document.querySelector("#file");
fileSelect.innerHTML = Object.entries(FILES).map(([file, label]) => `<option value="${file}">${label}</option>`).join("");
fileSelect.addEventListener("change", () => loadFile(fileSelect.value));
await loadFile(fileSelect.value);

// The CI smoke test waits for window.view.ready (see the repo README).
window.view = view;
