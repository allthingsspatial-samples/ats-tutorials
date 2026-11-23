# Generate branded ArcGIS Online thumbnails

Stamps a consistent branded thumbnail on every ArcGIS Online item you own, across the whole account or selected folders, from one PNG template. The item type goes in the header band and the item title in the footer band; the text auto-fits each band by measured pixel width. A dry run renders the thumbnails locally without touching the portal.

Blog post (step-by-step, with the direct downloads): https://www.allthingsspatial.io/pages/blog/automate-arcgis-online-thumbnails.html

- Video (PY-S01E01): https://www.youtube.com/watch?v=AHFU-Z42sic

## Files

- [`generate-branded-agol-thumbnails.ipynb`](generate-branded-agol-thumbnails.ipynb): the notebook (run it cell by cell in ArcGIS Pro or any Jupyter with the ArcGIS API for Python)
- [`generate-branded-agol-thumbnails.pyt`](generate-branded-agol-thumbnails.pyt): the same logic as an ArcGIS Pro Python toolbox tool
- [`generate-branded-agol-thumbnails.pyt.xml`](generate-branded-agol-thumbnails.pyt.xml): the toolbox's Pro help (keep it next to the .pyt)

To use the toolbox in ArcGIS Pro, put the `.pyt` and the `.pyt.xml` in the same folder and add the `.pyt` to your project (Catalog pane > Toolboxes > Add Toolbox). The blog post also offers both files as one `.zip`.

## Versions

ArcGIS Pro 3.x, run in the `arcgispro-py3` environment. Needs the ArcGIS API for Python and Pillow, which both ship with Pro. Signs in with your active Pro session (`GIS("pro")`).

## Source of truth

These files are byte-identical copies of the downloads served at `https://www.allthingsspatial.io/assets/downloads/`. When a tool changes, the site file and this copy are updated together and compared by SHA-256, so what you read here is what the blog's download button gives you.

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
