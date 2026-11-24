# Headless test for "Check Script Tool Parameters" (episode A4). Self-contained: writes a small .atbx with two script
# tools in tests\_scratch\script_tool_params\ (re-created on every run): GoodTool links to a script that reads 0-1 and sets
# the derived output 2; BadTool embeds a script that reads index 3 (the tool has 3 parameters), never reads input 1 and
# never sets derived output 2. Imports ATS-Starter.pyt and runs the tool the way Pro does.
# Run with the ArcGIS Pro Python:  propy.bat tests\test_check_script_tool.py      Exit code 0 = PASS.
import os, sys, json, shutil, zipfile
import arcpy

HERE = os.path.dirname(os.path.abspath(__file__))
PYT = os.path.join(os.path.dirname(HERE), "ATS-Starter.pyt")
S = os.path.join(HERE, "_scratch", "script_tool_params")
arcpy.env.overwriteOutput = True
fails = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg, flush=True)
    if not cond: fails.append(msg)


if os.path.exists(S): shutil.rmtree(S)
os.makedirs(os.path.join(S, "scripts"))
GOOD = '''import arcpy
fc = arcpy.GetParameterAsText(0)
n = arcpy.GetParameter(1)
arcpy.AddMessage("%s %s" % (fc, n))
arcpy.SetParameterAsText(2, str(n))
'''
BAD = '''import arcpy
fc = arcpy.GetParameterAsText(0)
x = arcpy.GetParameterAsText(3)
arcpy.AddMessage(fc)
'''
open(os.path.join(S, "scripts", "good_tool.py"), "w", encoding="utf-8").write(GOOD)


def params():   # labels live in tool.content.rc, as Pro writes them ($rc:<name>.title)
    return {"in_features": {"displayname": "$rc:in_features.title", "datatype": {"type": "GPFeatureLayer"}},
            "count": {"type": "optional", "displayname": "$rc:count.title", "datatype": {"type": "GPLong"}, "value": "3"},
            "result": {"type": "derived", "direction": "out", "displayname": "$rc:result.title", "datatype": {"type": "GPString"}}}


RC = json.dumps({"map": {"title": "Tool", "in_features.title": "Input Features", "count.title": "Count", "result.title": "Result"}})


tbx = os.path.join(S, "Test_Tools.atbx")
with zipfile.ZipFile(tbx, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("toolbox.content", json.dumps({"version": "1.0", "alias": "testtools", "displayname": "Test Tools",
                                              "toolsets": {"<root>": {"tools": ["GoodTool", "BadTool"]}}}))
    for t in ("GoodTool", "BadTool"):
        z.writestr(t + ".tool/tool.content", json.dumps({"type": "ScriptTool", "displayname": t, "product": "100",
                                                         "params": params()}))
        z.writestr(t + ".tool/tool.content.rc", RC)
    z.writestr("GoodTool.tool/tool.script.execute.link", r"..\..\scripts\good_tool.py")   # relative to <atbx>\<tool>.tool\
    z.writestr("BadTool.tool/tool.script.execute.py", BAD)

arcpy.ImportToolbox(PYT)
check(hasattr(arcpy, "CheckScriptToolParameters_atsstarter"), "toolbox imports and exposes CheckScriptToolParameters_atsstarter")
report = os.path.join(S, "report.md")
r = arcpy.CheckScriptToolParameters_atsstarter(tbx, report)
check(int(r.getOutput(1)) == 3, "3 issues found (all in BadTool): %s" % r.getOutput(1))
msgs = r.getMessages()
check("GoodTool" in msgs and "BadTool" in msgs, "both tools listed")
check("the script uses index 3, but the tool has 3 parameter(s) (0 to 2)" in msgs, "index 3 out of range flagged")
check("input 1 (Count) is never read" in msgs, "unread input flagged")
check("derived output 2 (Result) is never set" in msgs, "unset derived output flagged")
check("GoodTool:" not in r.getMessages(1), "no warnings for GoodTool: %s" % r.getMessages(1)[:300])
check(r.maxSeverity == 1, "issues are warnings (maxSeverity 1): %s" % r.maxSeverity)
txt = open(report, encoding="utf-8").read()
check("| 0 | Input Features | in_features |" in txt and "No issues." in txt and "Issues:" in txt, "Markdown report written")
check("good_tool.py" in txt and "(embedded)" in txt, "report names the linked and the embedded script")

# a clean toolbox (GoodTool only) gives 0 issues; a missing linked script is an issue
tbx2 = os.path.join(S, "Clean_Tools.atbx")
with zipfile.ZipFile(tbx2, "w") as z:
    z.writestr("toolbox.content", json.dumps({"version": "1.0", "alias": "cleantools", "toolsets": {"<root>": {"tools": ["GoodTool", "Lost"]}}}))
    for t, link in (("GoodTool", r"..\..\scripts\good_tool.py"), ("Lost", r"..\..\scripts\missing.py")):
        z.writestr(t + ".tool/tool.content", json.dumps({"type": "ScriptTool", "displayname": t, "params": params()}))
        z.writestr(t + ".tool/tool.content.rc", RC)
        z.writestr(t + ".tool/tool.script.execute.link", link)
r2 = arcpy.CheckScriptToolParameters_atsstarter(tbx2, None)
check(int(r2.getOutput(1)) == 1 and "script not found" in r2.getMessages(1), "missing script = 1 issue, GoodTool clean: %s" % r2.getOutput(1))

print("RESULT", "PASS" if not fails else "FAIL %d" % len(fails))
sys.exit(1 if fails else 0)
