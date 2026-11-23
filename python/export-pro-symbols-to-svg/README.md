# Export ArcGIS Pro symbols to SVG

Extracts ArcGIS Pro point symbols from a `.stylx` style to clean, scalable SVG, and optionally to PNG at a fixed pixel size: everything in a style, selected categories, or one symbol. A `.stylx` is a SQLite database whose ITEMS table holds each symbol's CIM JSON; the tool reads that JSON and writes the SVG directly, so the rendering core does not need arcpy.

Blog post (step-by-step, with the direct downloads): https://www.allthingsspatial.io/pages/blog/export-arcgis-pro-symbols-to-svg.html

- Video (PY-S01E02): https://www.youtube.com/watch?v=0Ifc8b1fNcA (also on the site: https://www.allthingsspatial.io/pages/watch/export-arcgis-pro-symbols-to-svg/)

## Files

- [`export-pro-symbols-to-svg.ipynb`](export-pro-symbols-to-svg.ipynb): the notebook
- [`export-pro-symbols-to-svg.pyt`](export-pro-symbols-to-svg.pyt): the same logic as an ArcGIS Pro Python toolbox tool
- [`export-pro-symbols-to-svg.pyt.xml`](export-pro-symbols-to-svg.pyt.xml): the toolbox's Pro help (keep it next to the .pyt)

To use the toolbox in ArcGIS Pro, put the `.pyt` and the `.pyt.xml` in the same folder and add the `.pyt` to your project (Catalog pane > Toolboxes > Add Toolbox). The blog post also offers both files as one `.zip`.

## Versions

ArcGIS Pro 3.x, run in the `arcgispro-py3` environment. The SVG core uses only the Python standard library (`sqlite3`, `json`). PNG output needs `cairosvg` or a local Inkscape install; without either, the SVGs are still written and the PNGs are skipped with a note.

## Source of truth

These files are byte-identical copies of the downloads served at `https://www.allthingsspatial.io/assets/downloads/`. When a tool changes, the site file and this copy are updated together and compared by SHA-256, so what you read here is what the blog's download button gives you.

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
