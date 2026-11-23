# ArcGIS Online data dictionary to Excel

Inventories your ArcGIS Online hosted feature services into a data dictionary: item metadata, every layer and table, geometry type, record count, spatial reference, and for each field the name, alias, type, length, nullability and domain (coded values or range). Writes TXT, CSV (one row per field) or a multi-sheet Excel workbook (Services, Layers, Fields). Scope it to the whole account, selected folders, one service, or a name search.

Blog post (step-by-step, with the direct downloads): https://www.allthingsspatial.io/pages/blog/arcgis-online-data-dictionary-to-excel.html

- Video (PY-S01E03): https://www.youtube.com/watch?v=fkZXUTszq0I
- Video (PY-S01E04): https://www.youtube.com/watch?v=wOe-eL5YT3w (also on the site: https://www.allthingsspatial.io/pages/watch/schedule-arcgis-online-notebook/)

## Files

- [`describe-feature-services.ipynb`](describe-feature-services.ipynb): the on-demand notebook
- [`describe-feature-services-scheduled.ipynb`](describe-feature-services-scheduled.ipynb): the scheduled version for an ArcGIS Online notebook task: each run overwrites one Excel item, so its link never changes (PY-S01E04)
- [`describe-feature-services.pyt`](describe-feature-services.pyt): the same logic as an ArcGIS Pro Python toolbox tool
- [`describe-feature-services.pyt.xml`](describe-feature-services.pyt.xml): the toolbox's Pro help (keep it next to the .pyt)

To use the toolbox in ArcGIS Pro, put the `.pyt` and the `.pyt.xml` in the same folder and add the `.pyt` to your project (Catalog pane > Toolboxes > Add Toolbox). The blog post also offers both files as one `.zip`.

## Versions

ArcGIS Pro 3.x (`arcgispro-py3`), or an ArcGIS Online notebook for the scheduled version. Needs the ArcGIS API for Python and `openpyxl` for Excel output (both ship with Pro). Signs in with your Pro session (`GIS("pro")`) or the notebook owner (`GIS("home")`); no credentials live in the files. Scheduled notebook runs use ArcGIS Online credits.

## Source of truth

These files are byte-identical copies of the downloads served at `https://www.allthingsspatial.io/assets/downloads/`. When a tool changes, the site file and this copy are updated together and compared by SHA-256, so what you read here is what the blog's download button gives you.

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
