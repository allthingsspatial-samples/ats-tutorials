# Enrich from service (ArcPy cursor template)

A template for attribute enrichment in three phases: read a worklist with a `SearchCursor` and close it, call an external service with no cursor open, then write the results back with a fresh `UpdateCursor` matched on `OID@`. The same where clause drives the read and the write, so the job is restartable and a metered service is not billed again for rows that already have values. Edit the `lookup()` function; everything else is a parameter. Dry run is on by default, a where clause is required, and a row cap limits each run. Test on a copy of your data first.

Blog post (step-by-step, with the direct downloads): https://www.allthingsspatial.io/pages/blog/arcpy-cursor-scope-pro-37.html

## Files

- [`enrich-from-service.ipynb`](enrich-from-service.ipynb): the notebook
- [`enrich-from-service.pyt`](enrich-from-service.pyt): the same template as an ArcGIS Pro Python toolbox tool
- [`enrich-from-service.pyt.xml`](enrich-from-service.pyt.xml): the toolbox's Pro help (keep it next to the .pyt)

To use the toolbox in ArcGIS Pro, put the `.pyt` and the `.pyt.xml` in the same folder and add the `.pyt` to your project (Catalog pane > Toolboxes > Add Toolbox). The blog post also offers both files as one `.zip`.

## Versions

ArcGIS Pro 3.x with ArcPy, written for the cursor lifetime change in ArcGIS Pro 3.7 (a cursor is closed when its `with` block exits). The notebook was saved with Python 3.13.

## Source of truth

These files are byte-identical copies of the downloads served at `https://www.allthingsspatial.io/assets/downloads/`. When a tool changes, the site file and this copy are updated together and compared by SHA-256, so what you read here is what the blog's download button gives you.

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
