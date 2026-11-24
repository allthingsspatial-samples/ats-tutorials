# How to Turn a Python Script into a Script Tool (PRO-S03 A4)

The script behind the script tool from the **Automate GIS** episode A4. The stand-alone script from A3 was changed in four places so ArcGIS Pro can run it as a geoprocessing tool:

1. `sys.argv` and defaults became `arcpy.GetParameterAsText(0..3)`.
2. `print()` became `arcpy.AddMessage`, `AddWarning` and `AddError`.
3. The silent loop got a step progressor (one step per county).
4. The mosaic path became a derived output, set with `arcpy.SetParameterAsText(4)`.

- Video: TBD (not uploaded yet; goes live 2026-11-28)
- Watch page and the other ArcGIS Pro episodes: https://www.allthingsspatial.io/learn/

## Files

- [`solar_screen_tool.py`](solar_screen_tool.py): the script tool's script, as shown and run on camera
- [`solar_screen_all_counties.py`](solar_screen_all_counties.py): the start state, the A3 stand-alone script it was made from
- [`Script_Tool_2026-11-18.atbx`](Script_Tool_2026-11-18.atbx): the project toolbox with the script tool `SolarScreenAllCounties`, as built on camera

The toolbox points to its script by a relative path, `scripts\solar_screen_tool.py` next to the toolbox (the layout of the data pack project). To use it, put the `.atbx` in the data pack project folder in place of the empty start-state toolbox. To keep the files as they are in this folder instead, open the tool's **Properties** > **Execution** and point the script file to `solar_screen_tool.py`. To build the tool yourself, see "Make the script tool" below.

## Versions

ArcGIS Pro 3.8 or later (recorded on 3.8.1), Basic license plus the Spatial Analyst extension.

## Make the script tool

1. In the Catalog pane, right-click your project toolbox > New > Script.
2. On the General page, name it (for example `SolarScreenAllCounties`) and give it a label.
3. On the Parameters page, add these five parameters in this order:

| Index | Label | Data type | Direction | Type | Default |
|---|---|---|---|---|---|
| 0 | Counties Workspace | Workspace | Input | Required | |
| 1 | Solar Model Inputs | Workspace | Input | Required | |
| 2 | Output Workspace | Workspace | Input | Required | |
| 3 | Distance to Lines (meters) | Double | Input | Optional | 8000 |
| 4 | Suitability Mosaic | Raster Dataset | Output | Derived | |

4. On the Execution page, point the script file to `solar_screen_tool.py`.
5. Click OK, open the tool and run it. The Messages show one line per county and the progressor steps through the counties.

The Starter Toolbox tool **Check Script Tool Parameters** ([`python/ats-starter-toolbox`](../ats-starter-toolbox/)) lists the parameters of every script tool in an `.atbx` and checks them against the script.

## Data

Data pack: https://downloads.allthingsspatial.io/pro-s03/a4/PRO-S03-A4_python-script-to-script-tool_data-pack_v1.zip (543 MB). It holds the start-state project with an empty toolbox, `data/Counties.gdb`, `data/Solar_Model_Inputs.gdb`, both scripts and the ATS Starter Toolbox. Per-file SHA-256 values are in its README.

Data sources: USGS 3DEP, Annual NLCD and PAD-US (US public domain); Census TIGER/Line (not copyrighted, credit the U.S. Census Bureau); HIFLD transmission lines; USFWS National Wetlands Inventory.

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
