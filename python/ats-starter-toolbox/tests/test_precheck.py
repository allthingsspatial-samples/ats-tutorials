# Headless test for "Check Feature Classes Before a Batch Run" (episode A2). Self-contained: builds synthetic data in
# tests\_scratch\precheck\ (re-created on every run), imports ATS-Starter.pyt and runs the tool the way Pro does.
# Run with the ArcGIS Pro Python:  propy.bat tests\test_precheck.py      Exit code 0 = PASS.
import os, sys, shutil
import numpy
import arcpy

HERE = os.path.dirname(os.path.abspath(__file__))
PYT = os.path.join(os.path.dirname(HERE), "ATS-Starter.pyt")
S = os.path.join(HERE, "_scratch", "precheck")
arcpy.env.overwriteOutput = True
fails = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg, flush=True)
    if not cond: fails.append(msg)


def square(x, y, size, sr):
    return arcpy.Polygon(arcpy.Array([arcpy.Point(x, y), arcpy.Point(x + size, y), arcpy.Point(x + size, y + size),
                                      arcpy.Point(x, y + size)]), sr)


if os.path.exists(S): shutil.rmtree(S)
os.makedirs(S)
sr = arcpy.SpatialReference(26917)
ws = arcpy.management.CreateFileGDB(S, "Zones.gdb")[0]
src = arcpy.management.CreateFileGDB(S, "Src.gdb")[0]
out = arcpy.management.CreateFileGDB(S, "Out.gdb")[0]

# zones (1 km squares): A inside the coverage, B inside but fully erased, C outside the coverage, Empty has no features
for nm, xy in (("Zone_A", (0, 0)), ("Zone_B", (2000, 0)), ("Zone_C", (10000, 10000)), ("Zone_Empty", None)):
    fc = arcpy.management.CreateFeatureclass(ws, nm, "POLYGON", spatial_reference=sr)[0]
    if xy:
        with arcpy.da.InsertCursor(fc, ["SHAPE@"]) as c:
            c.insertRow([square(xy[0], xy[1], 1000, sr)])
arcpy.management.CreateFeatureclass(ws, "Not_a_polygon", "POINT", spatial_reference=sr)
# coverage: a 3000 x 3000 m raster at 10 m (like the land cover in the A2 model)
ras = os.path.join(src, "Coverage")
arcpy.NumPyArrayToRaster(numpy.ones((300, 300), dtype=numpy.int16), arcpy.Point(0, 0), 10, 10).save(ras)
arcpy.management.DefineProjection(ras, sr)
# erase layer: covers all of Zone B and the west half of Zone A (0.5 km2 of A is left)
er = arcpy.management.CreateFeatureclass(src, "Exclusions", "POLYGON", spatial_reference=sr)[0]
with arcpy.da.InsertCursor(er, ["SHAPE@"]) as c:
    c.insertRow([square(1900, -100, 1200, sr)])
    c.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(-10, -10), arcpy.Point(500, -10), arcpy.Point(500, 1010),
                                            arcpy.Point(-10, 1010)]), sr)])

tbx = arcpy.ImportToolbox(PYT)
check(hasattr(arcpy, "PrecheckFeatureClasses_atsstarter"), "toolbox imports and exposes PrecheckFeatureClasses_atsstarter")

t1 = os.path.join(out, "Check_1")
r = arcpy.PrecheckFeatureClasses_atsstarter(ws, "*", ras, er, 0, t1)
runs = sorted(os.path.basename(p) for p in (r.getOutput(1) or "").split(";") if p)
check(runs == ["Zone_A"], "only Zone_A runs (coverage raster + erase layer): %s" % runs)
tab = {row[0]: row[1:] for row in arcpy.da.SearchCursor(t1, ["FC_Name", "Action", "Reason", "Row_Count", "Left_km2"])}
check(sorted(tab) == ["Zone_A", "Zone_B", "Zone_C", "Zone_Empty"], "table has one row per POLYGON feature class (point FC skipped): %s" % sorted(tab))
check(tab["Zone_Empty"][0] == "SKIP" and tab["Zone_Empty"][1] == "no features" and tab["Zone_Empty"][2] == 0, "Zone_Empty: SKIP, no features")
check(tab["Zone_C"][0] == "SKIP" and tab["Zone_C"][1] == "outside the coverage layer", "Zone_C: SKIP, outside the coverage layer")
check(tab["Zone_B"][0] == "SKIP" and tab["Zone_B"][3] == 0.0, "Zone_B: SKIP, 0 km2 left after the erase: %s" % (tab["Zone_B"],))
check(tab["Zone_A"][0] == "RUN" and abs(tab["Zone_A"][3] - 0.5) < 0.01, "Zone_A: RUN with 0.5 km2 left: %s" % (tab["Zone_A"],))
msgs = r.getMessages()
check("1 of 4 feature classes to run, 3 to skip." in msgs, "summary message")
check(r.maxSeverity == 1, "skips are reported as warnings (maxSeverity 1): %s" % r.maxSeverity)

# a minimum area above what is left turns Zone_A into a SKIP
r2 = arcpy.PrecheckFeatureClasses_atsstarter(ws, "Zone_A", ras, er, 0.6, os.path.join(out, "Check_2"))
check(not (r2.getOutput(1) or ""), "minimum area 0.6 km2 skips Zone_A (0.5 km2 left)")

# no coverage, no erase: every feature class with features runs
r3 = arcpy.PrecheckFeatureClasses_atsstarter(ws, "*", None, None, 0, os.path.join(out, "Check_3"))
runs3 = sorted(os.path.basename(p) for p in (r3.getOutput(1) or "").split(";") if p)
check(runs3 == ["Zone_A", "Zone_B", "Zone_C"], "without coverage/erase only the empty one is skipped: %s" % runs3)

# a feature-class coverage works too (union of the shapes)
cov_fc = arcpy.management.CreateFeatureclass(src, "Coverage_poly", "POLYGON", spatial_reference=sr)[0]
with arcpy.da.InsertCursor(cov_fc, ["SHAPE@"]) as c:
    c.insertRow([square(9500, 9500, 2000, sr)])
r4 = arcpy.PrecheckFeatureClasses_atsstarter(ws, "Zone_*", cov_fc, None, 0, os.path.join(out, "Check_4"))
runs4 = sorted(os.path.basename(p) for p in (r4.getOutput(1) or "").split(";") if p)
check(runs4 == ["Zone_C"], "feature-class coverage: only Zone_C touches it: %s" % runs4)

print("RESULT", "PASS" if not fails else "FAIL %d" % len(fails))
sys.exit(1 if fails else 0)
