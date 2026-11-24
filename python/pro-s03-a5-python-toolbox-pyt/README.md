# How to Build a Python Toolbox (.pyt) in ArcGIS Pro (PRO-S03 A5)

The finished `MyTools.pyt` from the **Automate GIS** episode A5: Esri's Python toolbox template with the toolbox label, alias and tool list changed, and the template's `Tool` class replaced by one tool, **Export Features to Folder**.

- Video: TBD (not uploaded yet; goes live 2026-11-29)
- Watch page and the other ArcGIS Pro episodes: https://www.allthingsspatial.io/learn/

## Files

- [`MyTools.pyt`](MyTools.pyt): the toolbox as it stands at the end of the episode

ArcGIS Pro writes the help files (`MyTools.pyt.xml`, `MyTools.ExportFeaturesToFolder.pyt.xml`) itself the first time it opens the toolbox, so they are not included.

## Versions

ArcGIS Pro 3.8 or later (recorded on 3.8.1), Basic license, no extension.

## Run it

1. In the Catalog pane, right-click Toolboxes > Add Toolbox and browse to `MyTools.pyt`. ArcGIS Pro asks whether you trust the code the first time (and after every edit).
2. Open **My Tools > Export Features to Folder**.
3. Fill in the parameters:

| Parameter | Type | Notes |
|---|---|---|
| Input Features | Feature layer | Required |
| Expression | SQL expression | Optional: export only the matching features |
| Output Folder | Folder | Required |
| Output Format | Value list | GeoJSON (WGS84), Shapefile, CSV (attributes only) or File Geodatabase (`Exports.gdb` in the folder) |
| Output Name | String | Optional: defaults to the layer name |
| Output | Derived | The path of the file or feature class written |

The core logic is in the `export_features()` function, so you can also call it from Python. After you edit the `.pyt`, right-click the toolbox > Refresh (modules the `.pyt` imports are not reloaded by Refresh).

The same tool is also in the [ATS Starter Toolbox](../ats-starter-toolbox/).

## Data

Data pack: https://downloads.allthingsspatial.io/pro-s03/a5/PRO-S03-A5_python-toolbox-pyt_data-pack_v1.zip (2.9 MB). It holds the start-state project, `data/A5_Inputs.gdb`, an empty `Exports/` folder and `finished/MyTools_FINAL.pyt` (the same code as this file). Per-file SHA-256 values are in its README.

Data sources: HIFLD transmission lines; Census TIGER/Line (not copyrighted, credit the U.S. Census Bureau).

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
