// Calcite components used by the layout in index.html.
import "@esri/calcite-components/components/calcite-shell";
import "@esri/calcite-components/components/calcite-shell-panel";
import "@esri/calcite-components/components/calcite-navigation";
import "@esri/calcite-components/components/calcite-navigation-logo";
import "@esri/calcite-components/components/calcite-panel";
import "@esri/calcite-components/components/calcite-notice";
import "@esri/calcite-components/components/calcite-button";
import "@esri/calcite-components/components/calcite-table";
import "@esri/calcite-components/components/calcite-table-row";
import "@esri/calcite-components/components/calcite-table-header";
import "@esri/calcite-components/components/calcite-table-cell";
// Map components.
import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-search";
import esriConfig from "@arcgis/core/config.js";
import { addressesToLocations, locationToAddress } from "@arcgis/core/rest/locator.js";
import Graphic from "@arcgis/core/Graphic.js";
import GraphicsLayer from "@arcgis/core/layers/GraphicsLayer.js";

// The ArcGIS Geocoding service. With an API key, requests go to the geocode-api host.
const GEOCODE_URL = "https://geocode-api.arcgis.com/arcgis/rest/services/World/GeocodeServer";
// Batch geocoding is billed as stored geocoding with no free tier, so the list is capped.
const MAX_ROWS = 25;

// Vite reads VITE_ARCGIS_TOKEN from .env.local (git-ignored) and inlines it at build time.
const apiKey = import.meta.env.VITE_ARCGIS_TOKEN?.trim() || "";
const mode = apiKey ? "key" : "no-key";

const mapElement = document.querySelector("arcgis-map");
const reverseResult = document.querySelector("#reverse-result");
const runBatch = document.querySelector("#run-batch");
const table = document.querySelector("#results");
const state = { mode, rows: 0, reverse: null, batch: null };

// Two graphics layers: the clicked point, and the batch results.
const clickLayer = new GraphicsLayer({ title: "Clicked point" });
const batchLayer = new GraphicsLayer({ title: "Batch results" });

// Read the address list. Each line: name,"street, city, state ZIP".
async function loadRows() {
  const response = await fetch("/data/capitols.csv");
  const lines = (await response.text()).trim().split(/\r?\n/).slice(1);
  return lines.slice(0, MAX_ROWS).map((line) => {
    const comma = line.indexOf(",");
    return { name: line.slice(0, comma), address: line.slice(comma + 1).replace(/^"|"$/g, "") };
  });
}

function cell(text, sub) {
  const td = document.createElement("calcite-table-cell");
  td.textContent = text;
  if (sub) {
    const small = document.createElement("div");
    small.className = "sub";
    small.textContent = sub;
    td.append(small);
  }
  return td;
}

function fillTable(items) {
  table.querySelectorAll("calcite-table-row:not([slot])").forEach((row) => row.remove());
  for (const item of items) {
    const row = document.createElement("calcite-table-row");
    row.append(cell(item.score ?? "-"), cell(item.name, item.match ?? item.address), cell(item.type ?? "-"));
    table.append(row);
  }
}

const rows = await loadRows();
state.rows = rows.length;
fillTable(rows);

if (mode === "key") {
  // One key for the whole app: basemap, search, reverse and batch geocoding requests all carry it.
  esriConfig.apiKey = apiKey;
  // The navigation basemap style needs the basemaps privilege.
  mapElement.basemap = "arcgis/navigation";

  // Address search box with suggestions, in the map's top-right corner.
  const search = document.createElement("arcgis-search");
  search.slot = "top-right";
  mapElement.append(search);
  runBatch.disabled = false;
} else {
  // No key: a basemap that needs no key, the notice, no search box and no geocoding requests.
  mapElement.basemap = "gray-vector";
  document.querySelector("#no-key").open = true;
  document.querySelector("#reverse-section").hidden = true;
}

await mapElement.viewOnReady();
mapElement.map.addMany([batchLayer, clickLayer]);

if (mode === "key") {
  // Reverse geocoding: map point in, nearest address out (one geocode, not stored).
  mapElement.addEventListener("arcgisViewClick", async (event) => {
    const point = event.detail.mapPoint;
    clickLayer.removeAll();
    clickLayer.add(new Graphic({
      geometry: point,
      symbol: { type: "simple-marker", style: "circle", color: [0, 121, 193], size: 14, outline: { color: "white", width: 2 } },
    }));
    reverseResult.textContent = "Finding the nearest address...";
    try {
      // featureTypes: return a street address, not a business name (POI) at the same spot.
      const candidate = await locationToAddress(GEOCODE_URL, { location: point, featureTypes: ["point-address", "street-address"] });
      state.reverse = { address: candidate.address, type: candidate.attributes.Addr_type };
      reverseResult.textContent = candidate.address;
    } catch {
      state.reverse = { address: null };
      reverseResult.textContent = "No address found here.";
    }
  });

  // Batch geocoding: every row in one geocodeAddresses request (billed as stored geocoding).
  runBatch.addEventListener("click", async () => {
    runBatch.loading = true;
    const addresses = rows.map((row, i) => ({ OBJECTID: i + 1, SingleLine: row.address }));
    let candidates;
    try {
      candidates = await addressesToLocations(GEOCODE_URL, { addresses, countryCode: "USA" });
    } catch (error) {
      // For example HTTP 403 when the key has no geocoding (stored) privilege.
      document.querySelector("#batch-hint").textContent = `Batch geocoding failed: ${error.message}`;
      state.batch = { error: error.message };
      runBatch.loading = false;
      return;
    }
    // ResultID matches the OBJECTID you sent, so each result finds its row.
    const results = candidates.map((c) => {
      const row = rows[c.attributes.ResultID - 1];
      return { name: row.name, address: row.address, score: Math.round(c.score), match: c.address, type: c.attributes.Addr_type, location: c.location };
    });
    // Lowest score first: those are the matches to check.
    results.sort((a, b) => a.score - b.score);
    batchLayer.removeAll();
    for (const r of results.filter((x) => x.location)) {
      batchLayer.add(new Graphic({
        geometry: r.location,
        symbol: { type: "simple-marker", style: "circle", color: [227, 139, 79], size: 12, outline: { color: "white", width: 2 } },
      }));
      batchLayer.add(new Graphic({
        geometry: r.location,
        symbol: { type: "text", text: String(r.score), color: "#151515", haloColor: "white", haloSize: 2, yoffset: 12, font: { size: 12, weight: "bold" } },
      }));
    }
    fillTable(results);
    state.batch = results.map(({ location, ...rest }) => rest);
    runBatch.loading = false;
    await mapElement.goTo(batchLayer.graphics.toArray());
  });
}

// For the smoke test and the tutorial's capture rig.
window.view = mapElement.view;
window.__atsSample = state;
