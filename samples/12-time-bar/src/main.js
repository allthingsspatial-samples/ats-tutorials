import "@esri/calcite-components/components/calcite-shell";
import "@esri/calcite-components/components/calcite-shell-panel";
import "@esri/calcite-components/components/calcite-navigation";
import "@esri/calcite-components/components/calcite-navigation-logo";
import "@esri/calcite-components/components/calcite-panel";
import "@esri/calcite-components/components/calcite-segmented-control";
import "@esri/calcite-components/components/calcite-segmented-control-item";
import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-zoom";
import "@arcgis/map-components/components/arcgis-time-bar";
import "@arcgis/map-components/components/arcgis-time-bar-slider";
import "@arcgis/map-components/components/arcgis-feature-table";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";
import TimeExtent from "@arcgis/core/time/TimeExtent.js";
import TimeInterval from "@arcgis/core/time/TimeInterval.js";
import * as reactiveUtils from "@arcgis/core/core/reactiveUtils.js";

// Esri's public sample item "USGS earthquakes 2019 June 18th" (GeoJSON, owner jsapi_team, the data used in
// Esri's Time Bar samples): 10,875 USGS earthquakes from 20 May to 19 June 2019. A fixed file, so every run
// shows the same earthquakes. Public, no key.
const QUAKES_ITEM = "0433d83530334b46b87c940dfc810589";
const DAY_MS = 24 * 60 * 60 * 1000;

const mapElement = document.querySelector("arcgis-map");
const timeBar = document.querySelector("arcgis-time-bar");
const table = document.querySelector("#table");
const modeControl = document.querySelector("#mode");

await mapElement.viewOnReady();

// 1. A time-aware layer: timeInfo names the date field. Without timeInfo the map's time does not filter it.
const quakes = new GeoJSONLayer({
  id: "quakes",
  portalItem: { id: QUAKES_ITEM },
  title: "Earthquakes",
  timeInfo: {
    startField: "time",
    interval: new TimeInterval({ value: 1, unit: "days" }),
  },
  outFields: ["mag", "place", "time", "depth"],
  renderer: {
    type: "simple",
    symbol: { type: "simple-marker", color: [255, 140, 60, 0.85], outline: { color: [255, 230, 200, 0.6], width: 0.5 } },
    visualVariables: [{ type: "size", field: "mag", stops: [{ value: 1, size: 3 }, { value: 7, size: 26 }] }],
  },
  popupEnabled: false,
});
mapElement.map.add(quakes);
await mapElement.whenLayerView(quakes);

// 2. The Time Bar: full extent from the layer, one stop per day, a one-day window to start.
await timeBar.componentOnReady();
// Round to whole days in UTC, the map's time zone (expandTo uses the computer's time zone unless told otherwise).
const full = quakes.timeInfo.fullTimeExtent.expandTo("days", "Etc/UTC");
timeBar.fullTimeExtent = full;
const DAILY = { interval: new TimeInterval({ value: 1, unit: "days" }) };
timeBar.stops = DAILY;
timeBar.timeExtent = new TimeExtent({ start: full.start, end: new Date(full.start.getTime() + DAY_MS) });

// Stops for instant mode: the times of the earthquakes of magnitude 6 or more. An instant matches only features at that
// exact moment, so daily (midnight) stops would match nothing here; stops at the data's own times match one each.
const { features: strong } = await quakes.queryFeatures({ where: "mag >= 6", outFields: ["time"], orderByFields: ["time ASC"] });
const STRONG = { dates: strong.map((f) => new Date(f.attributes.time)) };

// 3. The table follows the map's time: view-time-enabled (5.2) is set in index.html.
table.mapLayerId = quakes.id;
table.tableTemplate = {
  columnTemplates: [
    { type: "field", fieldName: "mag", label: "Magnitude" },
    { type: "field", fieldName: "place", label: "Place" },
    { type: "field", fieldName: "time", label: "Time (UTC)" },
    { type: "field", fieldName: "depth", label: "Depth (km)" },
  ],
};

// 4. Mode switch. Each mode expects its own time extent shape (see the Time Bar's timeExtent docs):
//    time-window = start and end, instant = start equals end, cumulative-from-start = start null.
//    Instant also switches to the strong-earthquake stops; the other modes use the daily stops.
const nextMidnight = (d) => new Date(Math.ceil(d.getTime() / DAY_MS) * DAY_MS);
function setMode(mode) {
  const current = timeBar.timeExtent;
  let anchor = current?.end ?? current?.start ?? full.start;
  timeBar.mode = mode;
  if (mode === "instant") {
    timeBar.stops = STRONG;
    const at = STRONG.dates.find((d) => d >= anchor) ?? STRONG.dates[0];
    timeBar.timeExtent = new TimeExtent({ start: at, end: at });
    return;
  }
  timeBar.stops = DAILY;
  anchor = nextMidnight(anchor); // back on a daily stop
  if (mode === "cumulative-from-start") timeBar.timeExtent = new TimeExtent({ start: null, end: anchor });
  else timeBar.timeExtent = new TimeExtent({ start: new Date(anchor.getTime() - DAY_MS), end: anchor });
}
modeControl.addEventListener("calciteSegmentedControlChange", () => setMode(modeControl.value));

// How many earthquakes fall in the current time (for the capture rig: values on screen = values narrated).
// Counts the whole layer (not only what is in view), like the table does.
function countInTime() {
  return quakes.queryFeatureCount({ timeExtent: mapElement.timeExtent, where: "1=1" });
}

// ---- In-page self-test, used by the smoke run. ----
async function selfTest() {
  const problems = [];
  for (const tag of ["arcgis-time-bar", "arcgis-time-bar-slider", "arcgis-feature-table"])
    if (!customElements.get(tag)) problems.push(`${tag} is not defined`);
  if (!quakes.timeInfo?.fullTimeExtent?.start) problems.push("layer timeInfo / fullTimeExtent missing");
  await reactiveUtils.whenOnce(() => mapElement.timeExtent?.start);
  const before = mapElement.timeExtent?.start?.getTime();
  if (!before) problems.push("view.timeExtent is null after the Time Bar is ready");
  const countBefore = await countInTime();
  await timeBar.next();
  await reactiveUtils.whenOnce(() => mapElement.timeExtent?.start?.getTime() !== before);
  const after = mapElement.timeExtent?.start?.getTime();
  if (after === before) problems.push("next() did not change view.timeExtent.start");
  const countAfter = await countInTime();
  if (table.viewTimeEnabled !== true) problems.push("feature table viewTimeEnabled is not true");
  if (timeBar.effectiveStops?.length !== 32) problems.push(`expected 32 daily stops, got ${timeBar.effectiveStops?.length}`);
  await timeBar.previous();
  if (STRONG.dates.length !== 12) problems.push(`expected 12 strong-earthquake stops, got ${STRONG.dates.length}`);
  for (const p of problems) console.error(`self-test: ${p}`);
  return {
    problems,
    before: new Date(before).toISOString(),
    after: new Date(after).toISOString(),
    countBefore,
    countAfter,
    stops: timeBar.effectiveStops?.length,
    total: (await quakes.queryFeatureCount()),
  };
}

// For the smoke test and the tutorial's capture rig.
window.view = mapElement.view;
window.__atsSample = { quakes, timeBar, table, setMode, countInTime, selfTest, strongDates: STRONG.dates };
