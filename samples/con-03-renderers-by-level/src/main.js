import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-legend";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";

const mapElement = document.querySelector("arcgis-map");
await mapElement.viewOnReady();

const fill = (color) => ({ type: "simple-fill", color, outline: { color: [255, 255, 255, 0.8], width: 0.5 } });
const toC = (f) => ((f - 32) * 5) / 9;

// One renderer per level of measurement. Each level allows more operations than the one before it,
// and each renderer only uses what its level allows.
const LEVELS = {
  // Nominal: names only. Equal or not equal; no order. Distinct hues, no ramp.
  nominal: {
    what: "Nominal: metro or nonmetro (from the 2023 RUCC). Categories with no order, so a UniqueValueRenderer with unrelated hues.",
    renderer: {
      type: "unique-value",
      field: "METRO",
      legendOptions: { title: "Metro status" },
      uniqueValueInfos: [
        { value: "Metro", label: "Metro", symbol: fill("#7b5cd6") },
        { value: "Nonmetro", label: "Nonmetro", symbol: fill("#3aa676") },
      ],
    },
  },
  // Ordinal: ranked codes. Order is real, but the gap between 2 and 3 is not the gap between 8 and 9.
  ordinal: {
    what: "Ordinal: Rural-Urban Continuum Code 1 (most urban) to 9 (most rural). Ranked, not measured, so one ordered single-hue ramp, one class per code.",
    renderer: {
      type: "unique-value",
      field: "RUCC",
      legendOptions: { title: "RUCC 2023" },
      uniqueValueInfos: ["#08306b", "#08519c", "#2171b5", "#4292c6", "#6baed6", "#9ecae1", "#bcd7ec", "#d4e5f4", "#e8f1fa"]
        .map((color, i) => ({ value: i + 1, label: `${i + 1}${i === 0 ? " most urban" : i === 8 ? " most rural" : ""}`, symbol: fill(color) })),
    },
  },
  // Interval: equal steps, but zero is arbitrary. Differences mean something; ratios do not.
  interval: {
    what: "Interval: mean annual temperature 1991-2020. Equal 5 °F classes in a ClassBreaksRenderer, because differences are meaningful.",
    note: "50 °F is not twice as warm as 25 °F: in °C that is 10.0 vs -3.9. The zero is arbitrary, so ratios mean nothing.",
    renderer: {
      type: "class-breaks",
      field: "TEMP_F",
      legendOptions: { title: "Mean annual temperature" },
      classBreakInfos: [[30, 35, "#2c7bb6"], [35, 40, "#abd9e9"], [40, 45, "#ffffbf"], [45, 50, "#fdae61"], [50, 55, "#d7191c"]]
        .map(([min, max, color]) => ({
          minValue: min, maxValue: max, symbol: fill(color),
          label: `${min}-${max} °F (${toC(min).toFixed(1)} to ${toC(max).toFixed(1)} °C)`,
        })),
    },
  },
  // Ratio: a true zero. "Twice as dense" is a real statement, so symbol size may be proportional.
  ratio: {
    what: "Ratio: people per km² (2024 population / land area). Zero means no people, so ClassBreaks color plus a size visual variable on the same field.",
    renderer: {
      type: "class-breaks",
      field: "DENSITY",
      legendOptions: { title: "People per km²" },
      classBreakInfos: [[0, 2, "#fde0c5"], [2, 10, "#facba6"], [10, 50, "#f59e72"], [50, 500, "#e05c5c"], [500, 2000, "#a3164d"]]
        .map(([min, max, color]) => ({
          minValue: min, maxValue: max, label: `${min}-${max}`,
          // Markers on a polygon layer draw at each county's centroid, so size can carry the value.
          symbol: { type: "simple-marker", color, outline: { color: [255, 255, 255, 0.9], width: 0.75 } },
        })),
      visualVariables: [{
        type: "size",
        field: "DENSITY",
        legendOptions: { title: "People per km² (symbol size)" },
        stops: [{ value: 1, size: 5 }, { value: 100, size: 18 }, { value: 2000, size: 44 }],
      }],
    },
  },
};

const counties = new GeoJSONLayer({
  url: new URL("data/colorado-counties.geojson", location.href).href,
  title: "Colorado counties",
  copyright: "US Census Bureau, USDA ERS, NOAA NCEI",
  popupTemplate: {
    title: "{NAME} County",
    content: "Metro status: {METRO}<br>RUCC 2023: {RUCC}<br>Mean temperature: {TEMP_F} °F<br>People per km²: {DENSITY}",
  },
});
mapElement.map.add(counties);

function show(level) {
  counties.renderer = LEVELS[level].renderer;
  document.querySelector("#what").textContent = LEVELS[level].what;
  document.querySelector("#note").textContent = LEVELS[level].note ?? "";
  for (const button of document.querySelectorAll("#levels button")) {
    button.setAttribute("aria-pressed", String(button.id === level));
  }
}
for (const level of Object.keys(LEVELS)) {
  document.querySelector(`#${level}`).addEventListener("click", () => show(level));
}
show("nominal");

// The CI smoke test waits for window.view.ready (see the repo README).
window.view = mapElement.view;
