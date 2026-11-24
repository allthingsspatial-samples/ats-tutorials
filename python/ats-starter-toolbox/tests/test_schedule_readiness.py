# Headless test for "Check Schedule Readiness" (episode A8). OFFLINE: the sign-in probe script is swapped for
# stand-ins that answer SIGNED_IN / ANONYMOUS / an error, so the test needs no sign-in and contacts no portal.
# It checks the separate-process probe, outputs (time stamp %t%, overwrite warning, missing folder, relative path),
# inputs (dataset path vs map layer vs missing), the CSV checklist, the dialog warning, the tool run through
# arcpy and that the toolbox still loads every tool. It never creates a schedule.
# Run with the ArcGIS Pro Python:  propy.bat tests\test_schedule_readiness.py      Exit code 0 = PASS.
import os, sys, shutil, csv, importlib.machinery, importlib.util
import arcpy
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
PYT = os.path.join(os.path.dirname(HERE), "ATS-Starter.pyt")
S = os.path.join(HERE, "_scratch", "schedule_readiness")
fails = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg, flush=True)
    if not cond: fails.append(msg)


if os.path.exists(S): shutil.rmtree(S)
os.makedirs(os.path.join(S, "Reports"))
gdb = arcpy.management.CreateFileGDB(S, "inputs.gdb")[0]
fc = arcpy.management.CreateFeatureclass(gdb, "Counties", "POLYGON", spatial_reference=4326)[0]

loader = importlib.machinery.SourceFileLoader("ats_starter_mod", PYT)
spec = importlib.util.spec_from_loader("ats_starter_mod", loader)
mod = importlib.util.module_from_spec(spec); loader.exec_module(mod)

# ---- sign-in probe in a separate process (stand-in scripts, offline) ----
REAL_PROBE = mod._SIGNIN_PROBE
check('GIS("pro")' in REAL_PROBE and "print" not in REAL_PROBE, "real probe uses GIS(\"pro\") and prints nothing")
for word, want in (("SIGNED_IN", "PASS"), ("ANONYMOUS", "FAIL")):
    mod._SIGNIN_PROBE = "import sys\nopen(sys.argv[1], 'w').write(%r)\n" % word
    st, note, secs = mod.test_signin_outside_pro()
    check(st == want, "probe %s -> %s (%s)" % (word, st, note))
mod._SIGNIN_PROBE = "raise RuntimeError('no')\n"
st, note, _ = mod.test_signin_outside_pro()
check(st == "FAIL" and "could not sign in" in note, "probe crash -> FAIL with advice")
mod._SIGNIN_PROBE = "import sys, os\nopen(sys.argv[1], 'w').write(str(os.getpid()) + ' ' + sys.executable)\n"
import tempfile
before = set(os.listdir(tempfile.gettempdir()))
mod.test_signin_outside_pro()
check(not [n for n in set(os.listdir(tempfile.gettempdir())) - before if n.startswith("ats_signin_")],
      "probe removes its temporary folder")
check(os.path.basename(mod._python_for_scheduled_runs()).lower() in ("pythonw.exe", "python.exe"),
      "probe runs the Pro Python (%s)" % os.path.basename(mod._python_for_scheduled_runs()))

# ---- outputs ----
rep = os.path.join(S, "Reports")
st, note = mod.check_output_location(os.path.join(rep, "Report_%t%.csv"))
check(st == "PASS" and "%t%" in note, "output with %t%: PASS")
st, note = mod.check_output_location(os.path.join(rep, "Report.csv"))
check(st == "WARN" and "overwritten" in note, "fixed output name: WARN overwritten")
st, _ = mod.check_output_location(os.path.join(S, "NoSuchFolder", "Report.csv"))
check(st == "FAIL", "missing output folder: FAIL")
st, _ = mod.check_output_location("Report.csv")
check(st == "FAIL", "relative output path: FAIL")
st, _ = mod.check_output_location(rep)
check(st == "PASS", "output folder: PASS")
check(os.listdir(rep) == [], "write test leaves nothing behind")
import datetime
stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
st, note = mod.check_output_location(os.path.join(rep, "Report_%s.csv" % stamp))
check(st == "PASS" and "Report_%t%.csv" in note, "%t% already replaced by geoprocessing: PASS")
st, _ = mod.check_output_location(os.path.join(rep, "Report_20190101000000.csv"))
check(st == "WARN", "an old 14-digit date in a name is not a time stamp: WARN")

# ---- inputs ----
st, _ = mod.check_input_dataset(fc)
check(st == "PASS", "dataset path: PASS")
lyr = arcpy.management.MakeFeatureLayer(fc, "Counties layer")[0]
st, note = mod.check_input_dataset(lyr)
check(st == "FAIL" and "map layer" in note and fc.lower() in note.lower(), "map layer: FAIL with the full path to use")
st, _ = mod.check_input_dataset(os.path.join(gdb, "Missing"))
check(st == "FAIL", "missing dataset: FAIL")

# ---- core function, checklist CSV ----
mod._SIGNIN_PROBE = "import sys\nopen(sys.argv[1], 'w').write('SIGNED_IN')\n"
out_csv = os.path.join(S, "checklist.csv")
r = mod.check_schedule_readiness([os.path.join(rep, "Report_%t%.csv")], [fc], True, out_csv)
check(r["ready"] and r["counts"]["FAIL"] == 0, "all good -> ready (%s)" % r["counts"])
rows = list(csv.DictReader(open(out_csv, encoding="utf-8-sig")))
check([x["check"] for x in rows] == ["ArcGIS Pro", "Sign in outside ArcGIS Pro", "Output", "Input", "Before you schedule"],
      "checklist rows in order")
r = mod.check_schedule_readiness([os.path.join(rep, "Report.csv")], [lyr], False)
check(not r["ready"] and r["counts"]["FAIL"] == 1 and r["counts"]["WARN"] >= 1, "layer input -> not ready (%s)" % r["counts"])
mod._SIGNIN_PROBE = REAL_PROBE

# ---- dialog ----
t = mod.CheckScheduleReadiness(); P = t.getParameterInfo()
check([p.name for p in P] == ["outputs", "inputs", "check_signin", "out_report", "ready"] and P[4].parameterType == "Derived",
      "parameters")
check(P[2].value is True, "default: test the sign-in")
check(t.category == "Scheduling", "category Scheduling")

# ---- through arcpy (validation + execute), sign-in test off so it stays offline ----
arcpy.ImportToolbox(PYT)
res = arcpy.atsstarter.CheckScheduleReadiness([os.path.join(rep, "NotYet_%t%.csv")], [fc], False,
                                              os.path.join(S, "checklist_tool.csv"))
check(str(res[1]).lower() == "true" or res.getOutput(1) in ("true", True), "tool run: Ready = true (%s)" % res.getOutput(1))
msgs = res.getMessages()
check("Ready to schedule: 4 pass, 1 warning(s), 0 fail" in msgs and "NotYet_%t%.csv gets a new name" in msgs,
      "tool run: %t% replaced by geoprocessing is still recognized (PASS), only the sign-in skip warns")
for name in ("BatchClipByFeatureClass", "PrecheckFeatureClasses", "FindScriptPaths", "CheckScriptToolParameters",
             "ExportFeaturesToFolder", "ExportProSymbols", "DescribeFeatureServices", "GenerateBrandedThumbnails",
             "CheckScheduleReadiness", "CopyMeTemplate"):
    check(hasattr(arcpy, name + "_atsstarter"), "toolbox exposes %s_atsstarter" % name)

print("RESULT", "PASS" if not fails else "FAIL %d" % len(fails))
sys.exit(1 if fails else 0)
