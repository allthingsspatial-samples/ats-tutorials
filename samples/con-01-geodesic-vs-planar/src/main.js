import "@arcgis/map-components/components/arcgis-map";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";
import * as areaOperator from "@arcgis/core/geometry/operators/areaOperator.js";
import * as geodeticAreaOperator from "@arcgis/core/geometry/operators/geodeticAreaOperator.js";

const mapElement = document.querySelector("arcgis-map");
await mapElement.viewOnReady();
const view = mapElement.view;

// Two countries of similar true size: Greenland (far north) and DR Congo (on the equator).
const countries = new GeoJSONLayer({
  url: new URL("data/countries.geojson", location.href).href,
  copyright: "Natural Earth",
  renderer: {
    type: "simple",
    symbol: { type: "simple-fill", color: [255, 122, 69, 0.45], outline: { color: [255, 122, 69, 1], width: 1 } },
  },
});
mapElement.map.add(countries);

// The geodetic operator needs its projection engine loaded once before execute().
if (!geodeticAreaOperator.isLoaded()) await geodeticAreaOperator.load();

// Ask the layer for the same polygons twice: once in Web Mercator, once in WGS84.
const query = { where: "1=1", outFields: ["name"], returnGeometry: true };
const mercator = await countries.queryFeatures({ ...query, outSpatialReference: { wkid: 3857 } });
const wgs84 = await countries.queryFeatures({ ...query, outSpatialReference: { wkid: 4326 } });

const million = (km2) => (km2 / 1e6).toFixed(2);
const rows = mercator.features.map((feature, i) => {
  // Planar: the flat-plane area of the projected shape, in the map's own units.
  const planar = areaOperator.execute(feature.geometry, { unit: "square-kilometers" });
  // Geodesic: the area on the ellipsoid, the way the ground actually measures.
  const geodesic = geodeticAreaOperator.execute(wgs84.features[i].geometry, { unit: "square-kilometers" });
  console.log(`${feature.attributes.name}: planar ${planar.toFixed(0)} km2, geodesic ${geodesic.toFixed(0)} km2`);
  return `<tr><td>${feature.attributes.name}</td><td>${million(planar)}</td><td>${million(geodesic)}</td>` +
    `<td>${(planar / geodesic).toFixed(2)}x</td></tr>`;
});
document.querySelector("#rows").innerHTML = rows.join("");

// The CI smoke test waits for window.view.ready (see the repo README).
window.view = view;
