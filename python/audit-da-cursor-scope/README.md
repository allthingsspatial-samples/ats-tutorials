# Audit arcpy.da cursor scope before ArcGIS Pro 3.7

Scans a folder of `.py` scripts, `.pyt` toolboxes and notebooks for code that uses an `arcpy.da` cursor after its `with` block has exited (for example `reset()` or a second loop). Such code worked before ArcGIS Pro 3.7 and raises `ValueError: I/O operation on closed file` after it. The tool parses the source with the standard-library `ast` module and executes nothing, so it is safe to run on code you have not read. Its findings are a review list, not a verdict.

Blog post (step-by-step, with the direct downloads): https://www.allthingsspatial.io/pages/blog/arcpy-cursor-scope-pro-37.html

## Files

- [`audit-da-cursor-scope.ipynb`](audit-da-cursor-scope.ipynb): the notebook
- [`audit-da-cursor-scope.pyt`](audit-da-cursor-scope.pyt): the same audit as an ArcGIS Pro Python toolbox tool
- [`audit-da-cursor-scope.pyt.xml`](audit-da-cursor-scope.pyt.xml): the toolbox's Pro help (keep it next to the .pyt)

To use the toolbox in ArcGIS Pro, put the `.pyt` and the `.pyt.xml` in the same folder and add the `.pyt` to your project (Catalog pane > Toolboxes > Add Toolbox). The blog post also offers both files as one `.zip`.

## Versions

Standard library only: runs in `arcgispro-py3` (ArcGIS Pro 3.x) or any plain Python 3.8 or later. It does not need ArcPy, because it reads the code and does not run it.

## Source of truth

These files are byte-identical copies of the downloads served at `https://www.allthingsspatial.io/assets/downloads/`. When a tool changes, the site file and this copy are updated together and compared by SHA-256, so what you read here is what the blog's download button gives you.

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
