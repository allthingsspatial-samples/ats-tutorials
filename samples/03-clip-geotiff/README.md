# 03 Clip GeoTIFF

Draw a box on the map and save the USGS 3DEP elevation inside it as a GeoTIFF, in one JavaScript file. It goes with the ATS Build episode BLD-S01E03, "Clip and Download a GeoTIFF in JavaScript (ArcGIS JS 5.0)".

- Data: the USGS 3D Elevation Program (3DEP) bare-earth DEM image service, `elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer`. It is public; the sample sets no API key.
- Map: one `ImageryLayer` on that service, drawn with its "Hillshade Elevation Tinted" raster function, over the `topo-vector` basemap (a 2D legacy basemap id).
- Draw: `SketchViewModel` (core) with the `rectangle` tool, on a `GraphicsLayer`, behind a plain HTML button.
- Clip: the image service's REST `exportImage` operation, called with `esriRequest` and `responseType: "blob"`. The query sends the box (`bbox`, `bboxSR` 3857), `size` at one pixel per 10 map units, `format=tiff`, `pixelType=F32` and `f=image`. No raster function is sent, so the file holds elevation values, not hillshade colors.
- Limit: the service publishes `maxImageWidth` and `maxImageHeight` (8000 x 8000 when this sample was written). The layer reads them as `imageMaxWidth` and `imageMaxHeight`, and the sample stops before asking for a larger image. Past the limit, the service answers with a short JSON error, not an image.
- Save: an object URL for the blob on a link with `download="3dep-clip.tif"`. No server of your own is involved.
- SDK: `@arcgis/core` and `@arcgis/map-components` 5.1.27 (pinned)
- Build tool: Vite

```bash
npm ci
npm run dev
```

If the hillshade does not draw or the export fails, reload the page: on 2026-10-23 the USGS service answered about 1 request in 40 with an HTTP 502 error.

Click **Draw a box**, drag on the map, and the browser saves `3dep-clip.tif`. Change `CELL_SIZE` in `src/main.js` for coarser or finer pixels.

To find the full 3DEP source files (whole tiles, with download links) for an area, see the 3DEP Source Locator: https://3dep.allthingsspatial.io/
