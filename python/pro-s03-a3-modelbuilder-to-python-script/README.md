# How to Turn a ModelBuilder Model into a Python Script (PRO-S03 A3)

The cleaned-up Python script from the **Automate GIS** episode A3. It started as the ModelBuilder export of the solar site model (Export > Export To Python File) and was then cleaned up:

1. Iterate Feature Classes became a `for` loop over `arcpy.ListFeatureClasses()`.
2. If Row Count Is and its precondition became an `if` block on Get Count.
3. Collect Values became a Python list.
4. Hard-coded paths became paths relative to the script (or command-line arguments).
5. `arcpy.env.overwriteOutput` is set to `True`, so the script can run again.

- Video: https://youtu.be/gxsCSTWj2XM (goes live 2026-11-27)
- Watch page and the other ArcGIS Pro episodes: https://www.allthingsspatial.io/learn/

## Files

- [`solar_screen_all_counties.py`](solar_screen_all_counties.py): the cleaned script shown and run on camera

The raw export that ModelBuilder writes is not included, because it holds the absolute paths of the recording machine. Exporting your own copy of the model gives you the same file with your paths.

## Versions

ArcGIS Pro 3.8 or later (recorded on 3.8.1), with the Spatial Analyst extension. It runs in the ArcGIS Pro Python (`arcgispro-py3`), with ArcGIS Pro open or closed.

## Run it

The script expects the episode folder layout: `scripts/` next to `data/Counties.gdb` and `data/Solar_Model_Inputs.gdb`. With the ArcGIS Pro Python:

```
propy.bat scripts\solar_screen_all_counties.py
```

or pass the three workspaces yourself:

```
propy.bat solar_screen_all_counties.py <counties_gdb> <inputs_gdb> <out_gdb>
```

The output geodatabase is created when it does not exist (default `reference/A3_reference.gdb`). The script prints one line per county and the total time.

## Data

Data pack: downloads.allthingsspatial.io pack for A3 is coming soon. The released A4 pack, https://downloads.allthingsspatial.io/pro-s03/a4/PRO-S03-A4_python-script-to-script-tool_data-pack_v1.zip, holds the same inputs (`data/Counties.gdb`, `data/Solar_Model_Inputs.gdb`) and this script in `scripts/`.

Data sources: USGS 3DEP, Annual NLCD and PAD-US (US public domain); Census TIGER/Line (not copyrighted, credit the U.S. Census Bureau); HIFLD transmission lines; USFWS National Wetlands Inventory.

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
