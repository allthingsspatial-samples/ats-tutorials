# 02 Imagery Swipe

A before/after slider on two dates of public satellite imagery, in one JavaScript file. It goes with the ATS Build episode BLD-S01E02, "Before/After Satellite Image Slider in JavaScript (ArcGIS JS 5.0)".

- Data: Esri's public multispectral Landsat image service, `landsat.arcgis.com/arcgis/rest/services/Landsat/MS/ImageServer`
- Layers: two `ImageryLayer`s on the same service. Each one keeps a single scene with a `definitionExpression` on the scene `Name`, and draws it with the service's "Natural Color with DRA" raster function
  - before: Landsat 7, 3 May 2000 (`p039r035_7dt20000503_z11_MS`)
  - after: Landsat 9, 3 July 2022 (`LC09_L1TP_039035_20220703_20230407_02_T1`)
- Slider: the `arcgis-swipe` component (map components). In 5.0 its layer lists are `startLayers` and `endLayers`; the Swipe widget is deprecated.
- Basemap: `dark-gray-vector`, a 2D (legacy) basemap id. The sample sets no API key and needs no `.env` file.
- SDK: `@arcgis/core` and `@arcgis/map-components` 5.1.27 (pinned)
- Build tool: Vite

```bash
npm ci
npm run dev
```

The page is `index.html` (the map and the swipe) and `src/main.js` (the layers). See before/after imagery in a full app: https://www.allthingsspatial.io/pages/landsat-explorer/
