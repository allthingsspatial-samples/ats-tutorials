# 01 USGS Earthquakes

The live USGS earthquake feed on a web map, in one JavaScript file. It goes with the ATS Build episode BLD-S01E01, "USGS Earthquake Map in JavaScript (ArcGIS JS 5.0)".

- Data: the USGS "all earthquakes, past 7 days" GeoJSON summary feed, read straight from `earthquake.usgs.gov`
- Layer: `GeoJSONLayer`, filtered to `type = 'earthquake'`, sized by magnitude, with a popup
- Basemap: `dark-gray-vector`, a 2D (legacy) basemap id. The sample sets no API key and needs no `.env` file.
- SDK: `@arcgis/core` 5.1.27 (pinned). It also builds and runs on 5.0.19.
- Build tool: Vite

```bash
npm ci
npm run dev
```

Everything is in `src/main.js`. See the full app this pattern comes from: https://www.allthingsspatial.io/pages/ring-of-fire/
