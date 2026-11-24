# How to Add If-Then Logic to a ModelBuilder Model (PRO-S03 A2)

The ModelBuilder toolbox from the **Automate GIS** episode A2, with the models as they were built and run on camera. It is the A1 county loop with a check added, so a county with no allowed area is skipped instead of failing the run:

1. **Solar Screen Each County** (`SolarScreenEachCounty`): Iterate Feature Classes walks the counties in `Counties.gdb`. For each county, Pairwise Erase removes wetlands and protected areas (`Allowed_area_%Name%`), **If Row Count Is** tests the result, and its True output is a precondition on Solar Site Screen, so the screen runs only for a county with allowed area left. Collect Values gathers the outputs.
2. **Model**: runs Solar Screen Each County as a nested model, then Mosaic To New Raster joins the county results into `Suitability_All_Counties`.
3. **Solar Site Screen** (`SolarSiteScreen`): the single-county suitability model the loop calls (erase wetlands and protected areas, slope score, distance-to-transmission-lines score, Weighted Sum).

- Video: https://youtu.be/Kv9qaTdkxyw (goes live 2026-11-25)
- Watch page and the other ArcGIS Pro episodes: https://www.allthingsspatial.io/learn/

## Files

- [`IfThen_Solar_Model_2026-11-18.atbx`](IfThen_Solar_Model_2026-11-18.atbx): the project toolbox with the three models

The data paths in the models were the absolute paths of the recording machine. In this copy they are relative to the folder that holds the toolbox (`data\Counties.gdb`, `data\Solar_Model_Inputs.gdb` and the output geodatabase `IfThen_Solar_Model_2026-11-18.gdb`). Nothing else in the models was changed.

## Versions

ArcGIS Pro 3.7 or later (recorded on 3.7.0), with the Spatial Analyst extension. If Row Count Is is a ModelBuilder-only tool, so this logic runs in ModelBuilder, not from Python. The Starter Toolbox tool **Check Feature Classes Before a Batch Run** ([`python/ats-starter-toolbox`](../ats-starter-toolbox/)) does the same row-count check in Python.

## Run it

1. Put the toolbox in your project folder, next to `data\Counties.gdb` and `data\Solar_Model_Inputs.gdb`, and create an empty file geodatabase `IfThen_Solar_Model_2026-11-18.gdb` there (or point the outputs at your own geodatabase).
2. In the Catalog pane, right-click **Toolboxes** > **Add Toolbox** and pick the `.atbx`.
3. Right-click **Model** > **Edit** to open it in ModelBuilder. If a data variable shows as not valid, double-click it and browse to your copy of the data.
4. Click **Run**. A county with no allowed area is skipped for that iteration, and the loop goes on to the next county.

## Data

Data pack: downloads.allthingsspatial.io pack for A2 is coming soon. The released A4 pack, https://downloads.allthingsspatial.io/pro-s03/a4/PRO-S03-A4_python-script-to-script-tool_data-pack_v1.zip, holds the same inputs (`data/Counties.gdb`, `data/Solar_Model_Inputs.gdb`).

Data sources: USGS 3DEP, Annual NLCD and PAD-US (US public domain); Census TIGER/Line (not copyrighted, credit the U.S. Census Bureau); HIFLD transmission lines; USFWS National Wetlands Inventory.

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
