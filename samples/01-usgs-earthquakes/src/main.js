import "@arcgis/core/assets/esri/themes/dark/main.css";
import Map from "@arcgis/core/Map.js";
import MapView from "@arcgis/core/views/MapView.js";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";

// USGS summary feed: every event of the past 7 days, as GeoJSON.
const FEED_URL =
  "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson";

const quakes = new GeoJSONLayer({
  url: FEED_URL,
  copyright: "USGS",
  // "time" is a number of milliseconds. Declare it as a date field.
  fields: [
    { name: "mag", type: "double" },
    { name: "place", type: "string" },
    { name: "time", type: "date" },
    { name: "type", type: "string" },
  ],
  // The feed also lists quarry blasts and explosions. Keep earthquakes only.
  definitionExpression: "type = 'earthquake'",
  // Ascending: small quakes draw on top, so a big circle never hides them.
  orderBy: [{ field: "mag", order: "ascending" }],
  // Ask the feed again every 5 minutes.
  refreshInterval: 5,
  renderer: {
    type: "simple",
    symbol: {
      type: "simple-marker",
      color: [255, 122, 69, 0.7],
      outline: { color: [255, 255, 255, 0.5], width: 0.5 },
    },
    visualVariables: [
      {
        type: "size",
        field: "mag",
        stops: [
          { value: 2.5, size: 3 },
          { value: 8, size: 36 },
        ],
      },
    ],
  },
  popupTemplate: {
    title: "Magnitude {mag}",
    content: "{place}<br>{time}",
    fieldInfos: [{ fieldName: "time", format: { dateFormat: "short-date-short-time" } }],
  },
});

// "dark-gray-vector" is a 2D (legacy) basemap id. This sample sets no
// esriConfig.apiKey and needs no .env file.
const map = new Map({ basemap: "dark-gray-vector", layers: [quakes] });

const view = new MapView({
  container: "viewDiv",
  map,
  center: [-165, 18], // lon, lat: the North Pacific
  zoom: 3,
});

// The CI smoke test waits for window.view.ready (see the repo README).
window.view = view;
