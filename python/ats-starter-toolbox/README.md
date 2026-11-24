# ATS Starter Toolbox

A small ArcGIS Pro Python toolbox (`ATS-Starter.pyt`) that grows by one tool per episode of the All Things Spatial **Automate GIS** series (PRO-S03, episodes A1 to A8). Every tool is plain Python that you can read, copy and change.

- Watch page and the ArcGIS Pro episodes: https://www.allthingsspatial.io/learn/
- Episode code: [A3](../pro-s03-a3-modelbuilder-to-python-script/), [A4](../pro-s03-a4-python-script-to-script-tool/), [A5](../pro-s03-a5-python-toolbox-pyt/), [A6](../pro-s03-a6-smart-tool-dialogs/)

## Add it to ArcGIS Pro

Keep `ATS-Starter.pyt` and its `.pyt.xml` help files in the same folder. In the Catalog pane, right-click Toolboxes > Add Toolbox and browse to `ATS-Starter.pyt`. ArcGIS Pro asks whether you trust the code the first time.

Versions: ArcGIS Pro 3.x, tested on 3.7.1, 3.7.3 and 3.8.1. The two ArcGIS Online tools use the ArcGIS API for Python that ships with ArcGIS Pro.

## Tools

| Tool (label) | Class | Category | Episode | What it does |
|---|---|---|---|---|
| Batch Clip to Each Feature Class | `BatchClipByFeatureClass` | Batch Processing | A1 How to Batch Process Data with ModelBuilder Iterators | Clips one layer (features or raster) to every polygon feature class in a workspace and names each output from a template: `{Name}` = feature class name, `{n}` = 0-based iteration number. Script twin of Iterate Feature Classes + `%Name%` + Collect Values. |
| Check Feature Classes Before a Batch Run | `PrecheckFeatureClasses` | Batch Processing | A2 How to Add If-Then Logic to a ModelBuilder Model | Marks every polygon feature class in a workspace RUN or SKIP: it must have features, touch an optional coverage layer and keep more than a minimum area after an optional erase layer is removed. Writes a RUN/SKIP table and returns the feature classes to run. Script twin of If Row Count Is + If Spatial Relationship Is. |
| Find Hard-Coded Paths in a Script | `FindScriptPaths` | Python Scripts | A3 How to Turn a ModelBuilder Model into a Python Script | Lists every hard-coded path in a Python script (for example a ModelBuilder export), says whether each exists, flags `overwriteOutput = False`, and with a base folder writes a cleaned copy where the paths become `os.path.join(HERE, ...)`. f-string paths are reported, not changed. |
| Check Script Tool Parameters | `CheckScriptToolParameters` | Python Scripts | A4 How to Turn a Python Script into a Script Tool | Lists the parameters of every script tool in an `.atbx` and checks each tool's script: every `GetParameterAsText(n)` / `GetParameter(n)` index exists, every input is read, every derived output is set. Optional Markdown report. Only literal indexes are checked. |
| Export Features to Folder | `ExportFeaturesToFolder` | Export | A5 How to Build a Python Toolbox (.pyt) in ArcGIS Pro | Exports a layer, or only the features that match an SQL expression, to GeoJSON (WGS84), a shapefile, a CSV table or a feature class in `Exports.gdb`. |
| Copy-Me Template | `CopyMeTemplate` | Templates | A5 | Starting point for a new tool: one of each common parameter type; `execute` only lists the inputs. Copy the class, rename it, add it to `self.tools`. |
| Export Pro Symbols to SVG/PNG | `ExportProSymbols` | Symbology | A6 How to Make Smart Tool Dialogs in ArcGIS Pro | Exports the point symbols of a style (`.stylx`) to SVG and/or PNG, one subfolder per category. The dialog is the A6 lesson: value lists filled from the style, a list that follows another list, parameters that switch on and off, optional-as-required with `setIDMessage("ERROR", 735)`. |
| Describe Feature Services | `DescribeFeatureServices` | ArcGIS Online | A7 How to Automate ArcGIS Online from ArcGIS Pro with Python | Writes a CSV report of the hosted feature layers you own in the portal ArcGIS Pro is signed in to (`GIS("pro")`, no credentials in code). Read only. |
| Generate Branded Thumbnails | `GenerateBrandedThumbnails` | ArcGIS Online | A7 | Draws a 600 x 400 PNG per hosted feature layer you own. Preview by default; with **Update Thumbnails on the Portal** checked it replaces each item thumbnail. Never touches items owned by anyone else. |
| Check Schedule Readiness | `CheckScheduleReadiness` | Scheduling | A8 How to Schedule a Geoprocessing Tool in ArcGIS Pro | Run it before **Run > Schedule**: checks the stored portal sign-in from a new windowless process (the way a scheduled run starts), full dataset paths instead of map layers, writable output folders and `%t%` in output names. Creates no schedule. |

Each tool keeps its core logic in a plain function (for example `export_features()`), so you can call it from Python as well.

## Notes from the episodes

- Tool class names and the toolbox `alias`: letters and numbers only, no underscores.
- After every edit ArcGIS Pro asks whether you trust the code; right-click the toolbox > Refresh. Modules the `.pyt` imports are not reloaded by Refresh.
- In ModelBuilder the inline variables are `%Name%` and `%n%`. A script tool cannot use the `%` form for its own templates: geoprocessing substitutes `%n%` in a string parameter before `execute()` runs. The Batch Clip tool therefore uses `{Name}` and `{n}`.
- `GIS("pro")` uses the portal ArcGIS Pro is signed in to. A scheduled run can sign in only if you checked **Sign in automatically** when you signed in to Pro.
- `%t%` in an output name becomes the run date and time (`yyyymmddhhmmss`), replaced before `execute()` runs.

## Tests

The `tests/` folder holds a headless test for the tools. Run them all with the ArcGIS Pro Python (Pro can stay closed):

```
propy.bat tests\run_all_tests.py
```

Each test builds its own synthetic data in `tests/_scratch/` and exits 0 on PASS. If a test fails with `ImportError: DLL load failed while importing lib`, a package in your user site-packages is shadowing the ArcGIS Pro one: run `set PYTHONNOUSERSITE=1` first. The test for Find Hard-Coded Paths is not published here, because its fixture uses sample drive paths.

## Add a tool

1. Write a class with `__init__`, `getParameterInfo`, `isLicensed`, `updateParameters`, `updateMessages` and `execute` ([Esri template for Python toolboxes](https://doc.esri.com/en/arcgis-pro/latest/arcpy/geoprocessing_and_python/a-template-for-python-toolboxes.html)).
2. Add the class to `self.tools` in `Toolbox.__init__`.
3. Add help metadata `ATS-Starter.<ClassName>.pyt.xml`.
4. Add a test in `tests/` and run `run_all_tests.py` again so the earlier tools keep passing.

## Data

The episode data packs are on downloads.allthingsspatial.io (A4 and A5 are released; see each episode folder). The A4 and A5 packs also carry a copy of this toolbox as it stood in that episode.

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
