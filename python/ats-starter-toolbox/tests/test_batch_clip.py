# Headless test for "Batch Clip to Each Feature Class" (episode A1). Self-contained: builds synthetic data in
# tests\_scratch\ (re-created on every run), imports ATS-Starter.pyt and runs the tool the way Pro does.
# Run with the ArcGIS Pro Python:  propy.bat tests\test_batch_clip.py      Exit code 0 = PASS.
import os, sys, shutil, json, time
import numpy
import arcpy

HERE = os.path.dirname(os.path.abspath(__file__))
PYT = os.path.join(os.path.dirname(HERE), "ATS-Starter.pyt")
S = os.path.join(HERE, "_scratch", "batch_clip")
arcpy.env.overwriteOutput = True
fails = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg, flush=True)
    if not cond: fails.append(msg)


if os.path.exists(S): shutil.rmtree(S)
os.makedirs(S)
sr = arcpy.SpatialReference(26917)
clip_ws = arcpy.management.CreateFileGDB(S, "Zones.gdb")[0]
out_ws = arcpy.management.CreateFileGDB(S, "Out.gdb")[0]
src_ws = arcpy.management.CreateFileGDB(S, "Src.gdb")[0]

# three square "zones" (polygon FCs) + one point FC the tool must skip
zones = {"Zone_A": (0, 0), "Zone_B": (2000, 0), "Zone_C": (0, 2000)}
for nm, (x, y) in zones.items():
    fc = arcpy.management.CreateFeatureclass(clip_ws, nm, "POLYGON", spatial_reference=sr)[0]
    with arcpy.da.InsertCursor(fc, ["SHAPE@"]) as c:
        c.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(x, y), arcpy.Point(x + 1000, y), arcpy.Point(x + 1000, y + 1000),
                                                arcpy.Point(x, y + 1000)]), sr)])
arcpy.management.CreateFeatureclass(clip_ws, "Not_a_polygon", "POINT", spatial_reference=sr)

# input features: a 10 x 10 grid of points every 300 m (0..2700) -> 4 x 4 = 16 inside each 1000 m zone (0,300,600,900)
pts = arcpy.management.CreateFeatureclass(src_ws, "Grid_points", "POINT", spatial_reference=sr)[0]
with arcpy.da.InsertCursor(pts, ["SHAPE@XY"]) as c:
    for i in range(10):
        for j in range(10):
            c.insertRow([(i * 300 + 50, j * 300 + 50)])
# input raster: 3000 x 3000 m at 10 m
ras = os.path.join(src_ws, "Ramp")
arcpy.NumPyArrayToRaster(numpy.arange(300 * 300, dtype=numpy.float32).reshape(300, 300), arcpy.Point(0, 0), 10, 10).save(ras)
arcpy.management.DefineProjection(ras, sr)

tbx = arcpy.ImportToolbox(PYT)
check(hasattr(arcpy, "BatchClipByFeatureClass_atsstarter"), "toolbox imports and exposes BatchClipByFeatureClass_atsstarter")

t0 = time.time()
r = arcpy.BatchClipByFeatureClass_atsstarter(clip_ws, "*", pts, out_ws, "{Name}_points")
msgs = r.getMessages()
outs = sorted(os.path.basename(p) for p in r.getOutput(0).split(";"))
check(outs == ["Zone_A_points", "Zone_B_points", "Zone_C_points"], "features: one output per polygon FC, {Name} expanded: %s" % outs)
counts = {o: int(arcpy.management.GetCount(os.path.join(out_ws, o))[0]) for o in outs}
check(counts == {"Zone_A_points": 16, "Zone_B_points": 12, "Zone_C_points": 12}, "features: points per zone 16/12/12 (grid 50..2750 step 300): %s" % counts)
check(not arcpy.Exists(os.path.join(out_ws, "Not_a_polygon_points")), "features: point FC in the clip workspace is skipped")
check("Collected 3 outputs" in msgs, "messages report the collected outputs")

r2 = arcpy.BatchClipByFeatureClass_atsstarter(clip_ws, "Zone_*", ras, out_ws, "Ramp_{n}")
outs2 = sorted(os.path.basename(p) for p in r2.getOutput(0).split(";"))
check(outs2 == ["Ramp_0", "Ramp_1", "Ramp_2"], "raster: {n} is the 0-based iteration number: %s" % outs2)
sizes = {o: (arcpy.Raster(os.path.join(out_ws, o)).width, arcpy.Raster(os.path.join(out_ws, o)).height) for o in outs2}
check(all(abs(w - 100) <= 1 and abs(h - 100) <= 1 for w, h in sizes.values()), "raster: each clip is ~100 x 100 cells: %s" % sizes)

r3 = arcpy.BatchClipByFeatureClass_atsstarter(clip_ws, "Zone_B", pts, out_ws, "Only_{Name}")
outs3 = [os.path.basename(p) for p in r3.getOutput(0).split(";")]
check(outs3 == ["Only_Zone_B"], "wildcard limits the iteration: %s" % outs3)

# validation: a template without {Name} or {n} raises a warning in updateMessages
import types
src = open(PYT, encoding="utf-8").read()
mod = types.ModuleType("ats_starter"); exec(compile(src, PYT, "exec"), mod.__dict__)
tool = mod.BatchClipByFeatureClass(); ps = tool.getParameterInfo()
ps[4].value = "same_name_every_time"; tool.updateMessages(ps)
check(ps[4].hasWarning(), "updateMessages warns when the name template has no inline variable")
# the reason for {Name}/{n}: geoprocessing substitutes %n% itself before execute() (kept as a regression probe)
r4 = arcpy.BatchClipByFeatureClass_atsstarter(clip_ws, "Zone_*", pts, out_ws, "Pct_%n%_{Name}")
outs4 = sorted(os.path.basename(p) for p in r4.getOutput(0).split(";"))
print("INFO percent-n probe outputs:", outs4, flush=True)
check(mod.expand_name_template("Suitability_{Name}_{n}", "Monroe_County", 2) == "Suitability_Monroe_County_2", "expand_name_template")

res = dict(test="test_batch_clip", passed=not fails, fails=fails, seconds=round(time.time() - t0, 1), counts=counts, raster_sizes=sizes)
json.dump(res, open(os.path.join(HERE, "_scratch", "test_batch_clip.result.json"), "w"), indent=1)
print("RESULT", "PASS" if not fails else "FAIL", json.dumps(res))
sys.exit(1 if fails else 0)
