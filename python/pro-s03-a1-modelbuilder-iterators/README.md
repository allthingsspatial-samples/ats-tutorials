# How to Batch Process Data with ModelBuilder Iterators (PRO-S03 A1)

The ModelBuilder toolbox from the **Automate GIS** episode A1, with the models as they were built and run on camera. The solar site screen model runs once for each county:

1. **Solar Screen Each County** (`SolarScreenEachCounty`): Iterate Feature Classes walks the counties in `Counties.gdb`, runs the Solar Site Screen model once for each one (output `Suitability_%Name%`), and Collect Values gathers the outputs.
2. **Model**: runs Solar Screen Each County as a nested model, then Mosaic To New Raster joins the county results into `Suitability_All_Counties`.
3. **Solar Site Screen** (`SolarSiteScreen`): the single-county suitability model the loop calls (erase wetlands and protected areas, slope score, distance-to-transmission-lines score, Weighted Sum).

- Video: https://youtu.be/G5Z9Mc7dFEg (goes live 2026-11-24)
- Watch page and the other ArcGIS Pro episodes: https://www.allthingsspatial.io/learn/

## Files

- [`Batch_Solar_Model_2026-11-17.atbx`](Batch_Solar_Model_2026-11-17.atbx): the project toolbox with the three models

The data paths in the models were the absolute paths of the recording machine. In this copy they are relative to the folder that holds the toolbox (`data\Counties.gdb`, `data\Solar_Model_Inputs.gdb` and the output geodatabase `Batch_Solar_Model_2026-11-17.gdb`). Nothing else in the models was changed.

## Versions

ArcGIS Pro 3.7 or later (recorded on 3.7.0), with the Spatial Analyst extension.

## Run it

1. Put the toolbox in your project folder, next to `data\Counties.gdb` and `data\Solar_Model_Inputs.gdb`, and create an empty file geodatabase `Batch_Solar_Model_2026-11-17.gdb` there (or point the outputs at your own geodatabase).
2. In the Catalog pane, right-click **Toolboxes** > **Add Toolbox** and pick the `.atbx`.
3. Right-click **Model** > **Edit** to open it in ModelBuilder. If a data variable shows as not valid, double-click it and browse to your copy of the data.
4. Click **Run**. The loop runs Solar Site Screen once per county, then the mosaic joins the results.

## Data

Data pack: downloads.allthingsspatial.io pack for A1 is coming soon. The released A4 pack, https://downloads.allthingsspatial.io/pro-s03/a4/PRO-S03-A4_python-script-to-script-tool_data-pack_v1.zip, holds the same inputs (`data/Counties.gdb`, `data/Solar_Model_Inputs.gdb`).

Data sources: USGS 3DEP, Annual NLCD and PAD-US (US public domain); Census TIGER/Line (not copyrighted, credit the U.S. Census Bureau); HIFLD transmission lines; USFWS National Wetlands Inventory.

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
