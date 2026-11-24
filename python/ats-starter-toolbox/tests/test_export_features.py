# Headless test for "Export Features to Folder" and "Copy-Me Template" (episode A5). Self-contained: builds
# synthetic data in tests\_scratch\export_features\ (re-created on every run), imports ATS-Starter.pyt and runs
# the tools the way Pro does. Run with the ArcGIS Pro Python:  propy.bat tests\test_export_features.py
# Exit code 0 = PASS.
import os, sys, shutil, json, csv, importlib.machinery, importlib.util
import arcpy
sys.dont_write_bytecode = True   # loading the .pyt as a module below must not leave __pycache__ in the toolbox folder

HERE = os.path.dirname(os.path.abspath(__file__))
PYT = os.path.join(os.path.dirname(HERE), "ATS-Starter.pyt")
S = os.path.join(HERE, "_scratch", "export_features")
arcpy.env.overwriteOutput = True
fails = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg, flush=True)
    if not cond: fails.append(msg)


if os.path.exists(S): shutil.rmtree(S)
os.makedirs(S)
out_dir = os.path.join(S, "out")
os.makedirs(out_dir)
sr = arcpy.SpatialReference(26917)   # NAD83 UTM 17N, so the GeoJSON must be projected to WGS84
src = arcpy.management.CreateFileGDB(S, "Src.gdb")[0]
fc = arcpy.management.CreateFeatureclass(src, "Lines", "POLYLINE", spatial_reference=sr)[0]
arcpy.management.AddField(fc, "VOLTAGE", "LONG")
arcpy.management.AddField(fc, "NAME", "TEXT", field_length=40)
volts = [69, 120, 138, 138, 230, 230, 230, 345, 345, 765]          # 6 lines >= 230
with arcpy.da.InsertCursor(fc, ["SHAPE@", "VOLTAGE", "NAME"]) as c:
    for i, v in enumerate(volts):
        x, y = 280000 + i * 1000, 4650000
        c.insertRow([arcpy.Polyline(arcpy.Array([arcpy.Point(x, y), arcpy.Point(x + 500, y + 800)]), sr), v, "Line %d" % i])

arcpy.ImportToolbox(PYT)
for t in ("BatchClipByFeatureClass", "ExportFeaturesToFolder", "CopyMeTemplate"):
    check(hasattr(arcpy, t + "_atsstarter"), "toolbox exposes %s_atsstarter" % t)

where = "VOLTAGE >= 230"
expected = {"GeoJSON": "HV_lines.geojson", "Shapefile": "HV_lines.shp", "CSV": "HV_lines.csv",
            "File Geodatabase": os.path.join("Exports.gdb", "HV_lines")}
for fmt, rel in expected.items():
    r = arcpy.ExportFeaturesToFolder_atsstarter(fc, where, out_dir, fmt, "HV_lines")
    out = r.getOutput(0)
    check(os.path.normcase(out) == os.path.normcase(os.path.join(out_dir, rel)), "%s: derived output path %s" % (fmt, out))
    check("Exporting 6 feature(s) as %s" % fmt in r.getMessages(), "%s: message reports 6 features" % fmt)
    if fmt == "GeoJSON":
        gj = json.load(open(out, encoding="utf-8"))
        xs = [pt[0] for f in gj["features"] for pt in f["geometry"]["coordinates"]]
        ys = [pt[1] for f in gj["features"] for pt in f["geometry"]["coordinates"]]
        check(len(gj["features"]) == 6, "GeoJSON: 6 features")
        check(all(-180 <= x <= 180 for x in xs) and all(-90 <= y <= 90 for y in ys), "GeoJSON: coordinates are longitude/latitude (WGS84)")
        check(sorted(f["properties"]["VOLTAGE"] for f in gj["features"]) == [230, 230, 230, 345, 345, 765], "GeoJSON: only VOLTAGE >= 230")
    elif fmt == "CSV":
        rows = list(csv.DictReader(open(out, encoding="utf-8-sig")))
        check(len(rows) == 6, "CSV: 6 rows (%d)" % len(rows))
        check("A CSV table holds the attributes only" in r.getMessages(), "CSV: attributes-only note in messages")
    else:
        n = int(arcpy.management.GetCount(out)[0])
        check(n == 6, "%s: 6 features (%d)" % (fmt, n))

# no expression -> all 10; blank name -> input name
r = arcpy.ExportFeaturesToFolder_atsstarter(fc, "", out_dir, "Shapefile", "")
check(os.path.basename(r.getOutput(0)) == "Lines.shp", "blank Output Name uses the input name (Lines.shp)")
check(int(arcpy.management.GetCount(r.getOutput(0))[0]) == 10, "no Expression exports all 10 features")
# expression with no match -> warning, empty output
r = arcpy.ExportFeaturesToFolder_atsstarter(fc, "VOLTAGE > 1000", out_dir, "File Geodatabase", "None_match")
check("matches no features" in r.getMessages(1), "no-match expression gives a warning")
check(int(arcpy.management.GetCount(r.getOutput(0))[0]) == 0, "no-match output is empty")
# the source is untouched
check(int(arcpy.management.GetCount(fc)[0]) == 10, "input still has 10 features")

# dialog behaviour: load the .pyt as a module and drive updateParameters like the Pro dialog does
loader = importlib.machinery.SourceFileLoader("ats_starter_mod", PYT)
spec = importlib.util.spec_from_loader("ats_starter_mod", loader)
mod = importlib.util.module_from_spec(spec); loader.exec_module(mod)
tool = mod.ExportFeaturesToFolder()
params = tool.getParameterInfo()
check([p.name for p in params] == ["in_features", "where_clause", "out_folder", "out_format", "out_name", "out_path"], "parameter order")
check(params[3].filter.list == ["GeoJSON", "Shapefile", "CSV", "File Geodatabase"] and params[3].value == "GeoJSON", "format value list + default GeoJSON")
check(params[1].parameterDependencies == ["in_features"], "Expression depends on Input Features")
check(params[5].parameterType == "Derived" and params[5].direction == "Output", "derived output parameter")
check(tool.category == "Export" and mod.CopyMeTemplate().category == "Templates", "categories Export / Templates")

# Copy-Me Template runs and only reports its inputs
r = arcpy.CopyMeTemplate_atsstarter(fc, "VOLTAGE", out_dir, "Option B", 5, True)
check("Choice = Option B" in r.getMessages() and "Number = 5" in r.getMessages(), "Copy-Me Template echoes its inputs")

print("RESULT", "FAIL %d" % len(fails) if fails else "PASS")
sys.exit(1 if fails else 0)
