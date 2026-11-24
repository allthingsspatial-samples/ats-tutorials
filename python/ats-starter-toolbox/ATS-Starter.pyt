# -*- coding: utf-8 -*-
r"""
ATS Starter Toolbox -- a small, generic ArcGIS Pro Python toolbox (.pyt)
=======================================================================

Companion toolbox for the All Things Spatial "Automate ArcGIS Pro" video series
(PRO-S03). Each episode adds or finishes one tool. Every tool is plain Python you
can read, copy and change.

Add it to a project: Catalog pane > Toolboxes > right-click > Add Toolbox, then
browse to ATS-Starter.pyt.

HOW TO ADD A TOOL
-----------------
1. Write a new class with __init__, getParameterInfo, isLicensed,
   updateParameters, updateMessages and execute (the Esri template, below).
2. The class NAME is letters and numbers only; the label can have spaces.
3. Add the class to self.tools in Toolbox.__init__.
4. Add a headless test in tests\ and run tests\run_all_tests.py with the
   ArcGIS Pro Python (propy.bat).

Esri template for Python toolboxes (Pro 3.7):
https://pro.arcgis.com/en/pro-app/latest/arcpy/geoprocessing_and_python/a-template-for-python-toolboxes.htm

License: MIT (see LICENSE). Requires ArcGIS Pro 3.x (tested on 3.7.1).

Tools
-----
- Batch Clip to Each Feature Class   (episode A1, ModelBuilder iterators)
- Check Feature Classes Before a Batch Run (episode A2, If-Then logic)
- Find Hard-Coded Paths in a Script  (episode A3, model to Python script)
- Check Script Tool Parameters       (episode A4, Python script to script tool)
- Export Features to Folder          (episode A5, Python toolboxes)
- Copy-Me Template                   (episode A5, start every new tool here)
- Export Pro Symbols to SVG/PNG      (episode A6, smart tool dialogs)
- Describe Feature Services         (episode A7, ArcGIS Online from ArcGIS Pro)
- Generate Branded Thumbnails       (episode A7, ArcGIS Online from ArcGIS Pro)
- Check Schedule Readiness          (episode A8, schedule a geoprocessing tool)
"""
import csv
import json
import math
import os
import re
import sqlite3
import time

import arcpy


# ---------------------------------------------------------------------------
# Toolbox
# ---------------------------------------------------------------------------
class Toolbox:
    def __init__(self):
        """The toolbox name shown in Catalog is the file name (ATS-Starter)."""
        self.label = "ATS Starter Toolbox"
        self.alias = "atsstarter"   # letters and numbers only
        # Register every tool here. Order = display order.
        self.tools = [BatchClipByFeatureClass, PrecheckFeatureClasses, FindScriptPaths, CheckScriptToolParameters, ExportFeaturesToFolder, ExportProSymbols, DescribeFeatureServices, GenerateBrandedThumbnails, CheckScheduleReadiness, CopyMeTemplate]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def expand_name_template(template, name, n):
    """Replace {Name} (the current feature class name) and {n} (the 0-based
    iteration number) in an output name. These mirror ModelBuilder's %Name% and
    %n% inline variables. A script tool cannot use the % form: geoprocessing
    substitutes %n% in string parameters before execute() runs (measured in
    tests/test_batch_clip.py), so every iteration would get the same name."""
    out = re.sub(r"\{name\}", name, template, flags=re.IGNORECASE)
    out = re.sub(r"\{n\}", str(n), out, flags=re.IGNORECASE)
    return out


def list_feature_classes(workspace, wildcard="", feature_type="All", recursive=False):
    """The Python equivalent of ModelBuilder's Iterate Feature Classes:
    feature class paths in a workspace (optionally its feature datasets)."""
    found = []
    ftype = feature_type or "All"
    for root, dirs, files in arcpy.da.Walk(workspace, datatype="FeatureClass", type=ftype):
        for f in files:
            if not wildcard or _wild_match(f, wildcard):
                found.append(os.path.join(root, f))
        if not recursive:
            dirs[:] = []   # top level only, like Recursive unchecked
    return sorted(found, key=lambda p: os.path.basename(p).lower())


def _wild_match(name, wildcard):
    rx = "^" + re.escape(wildcard).replace(r"\*", ".*") + "$"
    return re.match(rx, name, flags=re.IGNORECASE) is not None


# ---------------------------------------------------------------------------
# A1  Batch Clip to Each Feature Class
# ---------------------------------------------------------------------------
class BatchClipByFeatureClass:
    """For every polygon feature class in a workspace, clip one input layer
    (features or raster) to it and name the output after the feature class.
    This is the script-tool twin of a ModelBuilder model that uses
    Iterate Feature Classes + %Name% + Collect Values
    ({Name} and {n} here play the part of %Name% and %n%)."""

    def __init__(self):
        self.label = "Batch Clip to Each Feature Class"
        self.description = ("Clips one input layer to every polygon feature class "
                            "in a workspace and names each output from a template "
                            "such as {Name}_clip ({Name} = feature class name, {n} = 0-based iteration number).")
        self.category = "Batch Processing"
        self.canRunInBackground = True

    def getParameterInfo(self):
        p0 = arcpy.Parameter(displayName="Clip Workspace (polygon feature classes)",
                             name="clip_workspace", datatype="DEWorkspace",
                             parameterType="Required", direction="Input")
        p1 = arcpy.Parameter(displayName="Wildcard", name="wildcard",
                             datatype="GPString", parameterType="Optional",
                             direction="Input")
        p1.value = "*"
        p2 = arcpy.Parameter(displayName="Input Layer to Clip", name="in_layer",
                             datatype=["GPFeatureLayer", "GPRasterLayer"],
                             parameterType="Required", direction="Input")
        p3 = arcpy.Parameter(displayName="Output Workspace", name="out_workspace",
                             datatype="DEWorkspace", parameterType="Required",
                             direction="Input")
        p4 = arcpy.Parameter(displayName="Output Name Template", name="name_template",
                             datatype="GPString", parameterType="Required",
                             direction="Input")
        p4.value = "{Name}_clip"
        p5 = arcpy.Parameter(displayName="Output Datasets", name="out_datasets",
                             datatype="DEType", parameterType="Derived",
                             direction="Output", multiValue=True)
        return [p0, p1, p2, p3, p4, p5]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        tpl = parameters[4]
        if tpl.valueAsText and "%name%" not in tpl.valueAsText.lower() \
                and "%n%" not in tpl.valueAsText.lower():
            tpl.setWarningMessage("Without %Name% or %n% every iteration writes the "
                                  "same output name and only the last one is kept.")
        return

    def execute(self, parameters, messages):
        ws = parameters[0].valueAsText
        wildcard = parameters[1].valueAsText or "*"
        in_layer = parameters[2].valueAsText
        out_ws = parameters[3].valueAsText
        template = parameters[4].valueAsText
        result = batch_clip(ws, wildcard, in_layer, out_ws, template)
        parameters[5].value = ";".join(r["output"] for r in result["rows"])
        return

    def postExecute(self, parameters):
        return


def batch_clip(clip_workspace, wildcard, in_layer, out_workspace, template):
    """Core logic, callable from Python and from the tool. Returns a summary
    dict with one row per clip feature class."""
    d = arcpy.Describe(in_layer)
    is_raster = d.dataType in ("RasterDataset", "RasterLayer", "RasterBand", "MosaicDataset")
    fcs = [f for f in list_feature_classes(clip_workspace, "" if wildcard == "*" else wildcard,
                                           "Polygon")]
    if not fcs:
        arcpy.AddWarning("No polygon feature classes match '%s' in %s." % (wildcard, clip_workspace))
    rows = []
    t_all = time.time()
    arcpy.SetProgressor("step", "Clipping...", 0, max(len(fcs), 1), 1)
    for n, fc in enumerate(fcs):
        name = os.path.basename(fc)
        out_name = arcpy.ValidateTableName(expand_name_template(template, name, n), out_workspace)
        out = os.path.join(out_workspace, out_name)
        arcpy.SetProgressorLabel("%d of %d: %s" % (n + 1, len(fcs), name))
        t0 = time.time()
        if is_raster:
            arcpy.management.Clip(in_layer, "#", out, fc, "#", "ClippingGeometry",
                                  "NO_MAINTAIN_EXTENT")
            r = arcpy.Raster(out)
            size = "%d x %d cells" % (r.width, r.height)
        else:
            arcpy.analysis.PairwiseClip(in_layer, fc, out)
            size = "%s features" % arcpy.management.GetCount(out)[0]
        secs = round(time.time() - t0, 1)
        arcpy.AddMessage("%d  %s -> %s  (%s, %.1f s)" % (n, name, out_name, size, secs))
        rows.append(dict(n=n, name=name, output=out, size=size, seconds=secs))
        arcpy.SetProgressorPosition()
    arcpy.ResetProgressor()
    total = round(time.time() - t_all, 1)
    arcpy.AddMessage("Collected %d outputs in %.1f s." % (len(rows), total))
    return dict(rows=rows, seconds=total)


# ---------------------------------------------------------------------------
# A2  Check Feature Classes Before a Batch Run
# ---------------------------------------------------------------------------
class PrecheckFeatureClasses:
    """Before a batch run, checks every polygon feature class in a workspace
    and decides RUN or SKIP for each one. It is the script twin of the
    ModelBuilder If-Then tools used in episode A2: If Row Count Is (does the
    feature class have features? is anything left after the erase?) and
    If Spatial Relationship Is (does it touch the data coverage?)."""

    def __init__(self):
        self.label = "Check Feature Classes Before a Batch Run"
        self.description = ("Checks every polygon feature class in a workspace before a batch run: "
                            "it must have features, overlap a coverage layer (optional) and keep a "
                            "minimum area after an erase layer is removed (optional). Writes a "
                            "RUN/SKIP table and returns the feature classes to run.")
        self.category = "Batch Processing"

    def getParameterInfo(self):
        p0 = arcpy.Parameter(displayName="Workspace (polygon feature classes)",
                             name="workspace", datatype="DEWorkspace",
                             parameterType="Required", direction="Input")
        p1 = arcpy.Parameter(displayName="Wildcard", name="wildcard",
                             datatype="GPString", parameterType="Optional",
                             direction="Input")
        p1.value = "*"
        p2 = arcpy.Parameter(displayName="Coverage Layer", name="coverage_layer",
                             datatype=["GPFeatureLayer", "GPRasterLayer"],
                             parameterType="Optional", direction="Input")
        p3 = arcpy.Parameter(displayName="Erase Layer", name="erase_layer",
                             datatype="GPFeatureLayer", parameterType="Optional",
                             direction="Input")
        p3.filter.list = ["Polygon"]
        p4 = arcpy.Parameter(displayName="Minimum Area Left (square kilometers)",
                             name="min_area_km2", datatype="GPDouble",
                             parameterType="Optional", direction="Input")
        p4.value = 0.0
        p5 = arcpy.Parameter(displayName="Output Table", name="out_table",
                             datatype="DETable", parameterType="Required",
                             direction="Output")
        p6 = arcpy.Parameter(displayName="Feature Classes to Run", name="run_list",
                             datatype="DEFeatureClass", parameterType="Derived",
                             direction="Output", multiValue=True)
        return [p0, p1, p2, p3, p4, p5, p6]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # the minimum area only matters when there is something to erase
        parameters[4].enabled = bool(parameters[3].value)
        return

    def updateMessages(self, parameters):
        if parameters[4].value is not None and parameters[4].value < 0:
            parameters[4].setErrorMessage("The minimum area cannot be negative.")
        return

    def execute(self, parameters, messages):
        result = precheck_feature_classes(parameters[0].valueAsText,
                                          parameters[1].valueAsText or "*",
                                          parameters[2].valueAsText,
                                          parameters[3].valueAsText,
                                          parameters[4].value or 0.0,
                                          parameters[5].valueAsText)
        parameters[6].value = ";".join(r["path"] for r in result["rows"] if r["action"] == "RUN")
        return

    def postExecute(self, parameters):
        return


def _coverage_polygon(layer):
    """The coverage of a raster is its extent; the coverage of features is the
    union of their shapes."""
    d = arcpy.Describe(layer)
    if d.dataType in ("RasterDataset", "RasterLayer", "RasterBand", "MosaicDataset"):
        return d.extent.polygon
    geom = None
    with arcpy.da.SearchCursor(layer, ["SHAPE@"]) as cur:
        for (g,) in cur:
            if g is None:
                continue
            geom = g if geom is None else geom.union(g)
    return geom


def precheck_feature_classes(workspace, wildcard="*", coverage_layer=None, erase_layer=None,
                             min_area_km2=0.0, out_table=None):
    """Core logic, callable from Python and from the tool. Returns a dict with
    one row per polygon feature class: action RUN or SKIP and the reason."""
    fcs = list_feature_classes(workspace, "" if wildcard in (None, "", "*") else wildcard, "Polygon")
    cov = cov_sr = None
    if coverage_layer:
        cov = _coverage_polygon(coverage_layer)
        cov_sr = arcpy.Describe(coverage_layer).spatialReference
    rows = []
    for n, fc in enumerate(fcs):
        name = os.path.basename(fc)
        count = int(arcpy.management.GetCount(fc)[0])          # If Row Count Is
        area = left = 0.0
        action, reason = "RUN", ""
        if count == 0:
            action, reason = "SKIP", "no features"
        else:
            with arcpy.da.SearchCursor(fc, ["SHAPE@"]) as cur:
                shapes = [g for (g,) in cur if g is not None]
            area = sum(g.area for g in shapes) / 1e6
            left = area
            if cov is not None:                                  # If Spatial Relationship Is (Intersects)
                touches = any(not (g.projectAs(cov_sr) if cov_sr else g).disjoint(cov) for g in shapes)
                if not touches:
                    action, reason = "SKIP", "outside the coverage layer"
            if action == "RUN" and erase_layer:                  # If Row Count Is on the erase result
                tmp = r"memory\precheck_left"
                arcpy.analysis.PairwiseErase(fc, erase_layer, tmp)
                with arcpy.da.SearchCursor(tmp, ["SHAPE@AREA"]) as cur:
                    left = sum(a for (a,) in cur) / 1e6
                arcpy.management.Delete(tmp)
                if left <= (min_area_km2 or 0.0):
                    action, reason = "SKIP", "%.2f km2 left after the erase (minimum %.2f)" % (left, min_area_km2 or 0.0)
        rows.append(dict(n=n, name=name, path=fc, rows=count, area_km2=round(area, 2),
                         left_km2=round(left, 2), action=action, reason=reason))
        msg = "%d  %s: %s%s" % (n, name, action, (" - " + reason) if reason else "")
        arcpy.AddWarning(msg) if action == "SKIP" else arcpy.AddMessage(msg)
    if out_table:
        folder, tname = os.path.split(out_table)
        if arcpy.Exists(out_table):
            arcpy.management.Delete(out_table)
        arcpy.management.CreateTable(folder, tname)
        for f, t, ln in (("FC_Name", "TEXT", 128), ("Iteration", "SHORT", None), ("Row_Count", "LONG", None),
                         ("Area_km2", "DOUBLE", None), ("Left_km2", "DOUBLE", None), ("Action", "TEXT", 8),
                         ("Reason", "TEXT", 255)):
            arcpy.management.AddField(out_table, f, t, field_length=ln)
        with arcpy.da.InsertCursor(out_table, ["FC_Name", "Iteration", "Row_Count", "Area_km2", "Left_km2",
                                               "Action", "Reason"]) as cur:
            for r in rows:
                cur.insertRow([r["name"], r["n"], r["rows"], r["area_km2"], r["left_km2"], r["action"], r["reason"]])
    n_run = sum(1 for r in rows if r["action"] == "RUN")
    arcpy.AddMessage("%d of %d feature classes to run, %d to skip." % (n_run, len(rows), len(rows) - n_run))
    return dict(rows=rows, run=n_run, skip=len(rows) - n_run)


# ---------------------------------------------------------------------------
# A3  Find Hard-Coded Paths in a Script
# ---------------------------------------------------------------------------
class FindScriptPaths:
    """Lists every hard-coded path in a Python script, for example a model
    exported from ModelBuilder (Export > Export To Python File), says whether
    each one exists, and can write a cleaned copy where the paths inside a
    base folder become relative to the script. Episode A3 uses it on the
    exported solar model."""

    def __init__(self):
        self.label = "Find Hard-Coded Paths in a Script"
        self.description = ("Lists the hard-coded paths in a Python script (for example a "
                            "ModelBuilder export), checks that each one exists, flags "
                            "overwriteOutput = False, and can write a cleaned copy with the "
                            "paths inside a base folder made relative to the script.")
        self.category = "Python Scripts"

    def getParameterInfo(self):
        in_script = arcpy.Parameter(displayName="Input Python Script", name="in_script",
                                    datatype="DEFile", parameterType="Required", direction="Input")
        in_script.filter.list = ["py"]
        base_folder = arcpy.Parameter(displayName="Base Folder (paths inside it become relative)",
                                      name="base_folder", datatype="DEFolder",
                                      parameterType="Optional", direction="Input")
        out_table = arcpy.Parameter(displayName="Output Report Table", name="out_table",
                                    datatype="DETable", parameterType="Optional", direction="Output")
        out_script = arcpy.Parameter(displayName="Cleaned Copy of the Script", name="out_script",
                                     datatype="DEFile", parameterType="Optional", direction="Output")
        out_script.filter.list = ["py"]
        count = arcpy.Parameter(displayName="Hard-Coded Paths Found", name="path_count",
                                datatype="GPLong", parameterType="Derived", direction="Output")
        return [in_script, base_folder, out_table, out_script, count]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # a cleaned copy only makes sense with a base folder
        parameters[3].enabled = bool(parameters[1].value)
        return

    def updateMessages(self, parameters):
        p_in, p_out = parameters[0], parameters[3]
        if p_in.value and p_out.value and os.path.normcase(os.path.abspath(p_in.valueAsText)) == \
                os.path.normcase(os.path.abspath(p_out.valueAsText)):
            p_out.setErrorMessage("Write the cleaned copy to a new file; the input script is never changed.")
        return

    def execute(self, parameters, messages):
        result = find_script_paths(parameters[0].valueAsText, parameters[1].valueAsText,
                                   parameters[2].valueAsText,
                                   parameters[3].valueAsText if parameters[3].enabled else None)
        parameters[4].value = len(result["paths"])
        return

    def postExecute(self, parameters):
        return


_DRIVE_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\[^\\]+\\)")


def _string_tokens(source):
    """(start, end, text, value, is_fstring) for every string literal, from the
    tokenizer, so comments and code are never mistaken for paths. Python 3.12
    and later (ArcGIS Pro 3.7 ships 3.13) split an f-string into FSTRING_START /
    MIDDLE / END tokens; older versions give one STRING token."""
    import ast
    import io
    import tokenize
    out = []
    fs_start = getattr(tokenize, "FSTRING_START", None)
    fs_end = getattr(tokenize, "FSTRING_END", None)
    f_open = None
    src_lines = source.splitlines(keepends=True)
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if fs_start is not None and tok.type == fs_start:
            f_open = (tok.start, [])
            continue
        if f_open is not None:
            if tok.type == fs_end:
                (sr, sc), (er, ec) = f_open[0], tok.end
                text = src_lines[sr - 1][sc:ec] if sr == er else "".join(f_open[1])
                out.append((f_open[0], tok.end, text, None, True))
                f_open = None
            else:
                f_open[1].append(tok.string)
            continue
        if tok.type != tokenize.STRING:
            continue
        prefix = tok.string[:tok.string.index(tok.string.lstrip("rRbBuUfF")[0])].lower()
        if "f" in prefix or "b" in prefix:
            out.append((tok.start, tok.end, tok.string, None, "f" in prefix))
            continue
        try:
            out.append((tok.start, tok.end, tok.string, ast.literal_eval(tok.string), False))
        except (ValueError, SyntaxError):
            continue
    return out


def find_script_paths(in_script, base_folder=None, out_table=None, out_script=None):
    """Core logic, callable from Python and from the tool. Returns a dict with
    one row per hard-coded path: line, path, exists, relative (or ''), and the
    lines that set overwriteOutput to False."""
    with open(in_script, encoding="utf-8") as f:
        source = f.read()
    script_dir = os.path.dirname(os.path.abspath(in_script))
    base = os.path.normcase(os.path.abspath(base_folder)) if base_folder else None
    rows, edits = [], []
    for start, end, text, value, is_f in _string_tokens(source):
        if is_f:
            inner = text.lstrip("rRfF")[1:]
            if _DRIVE_PATH.match(inner.lstrip("\"'")):
                rows.append(dict(line=start[0], path=inner.strip("\"'"), exists="?", relative="",
                                 note="f-string: edit it by hand"))
            continue
        if not isinstance(value, str) or not _DRIVE_PATH.match(value):
            continue
        p = value.rstrip("\\/")
        exists = "yes" if (os.path.exists(p) or arcpy.Exists(p)) else "no"
        rel = ""
        if base and os.path.normcase(os.path.abspath(p)).startswith(base + os.sep):
            rel = os.path.relpath(p, script_dir)
            parts = [x for x in re.split(r"[\\/]", rel) if x]
            expr = "os.path.join(HERE, %s)" % ", ".join('"%s"' % x for x in parts)
            edits.append((start, end, expr))
        rows.append(dict(line=start[0], path=value, exists=exists, relative=rel,
                         note="" if exists == "yes" else "not found on this computer"))
    overwrite_false = [i + 1 for i, ln in enumerate(source.splitlines())
                       if re.search(r"overwriteOutput\s*=\s*False", ln) and not ln.lstrip().startswith("#")]

    for r in rows:
        msg = "line %d: %s  [exists: %s]%s%s" % (r["line"], r["path"], r["exists"],
                                                  ("  -> " + r["relative"]) if r["relative"] else "",
                                                  ("  (" + r["note"] + ")") if r["note"] else "")
        arcpy.AddWarning(msg) if r["exists"] != "yes" else arcpy.AddMessage(msg)
    for ln in overwrite_false:
        arcpy.AddWarning("line %d: overwriteOutput = False - a second run stops at the first existing output" % ln)
    arcpy.AddMessage("%d hard-coded path(s), %d inside the base folder, %d not found." % (
        len(rows), len(edits), sum(1 for r in rows if r["exists"] == "no")))

    if out_script:
        lines = source.splitlines(keepends=True)
        for (sr, sc), (er, ec), expr in sorted(edits, reverse=True):   # back to front keeps positions valid
            if sr != er:
                continue                                              # multi-line string: leave it
            ln = lines[sr - 1]
            lines[sr - 1] = ln[:sc] + expr + ln[ec:]
        header = ("import os\nHERE = os.path.dirname(os.path.abspath(__file__))  "
                  "# added by Find Hard-Coded Paths\n")
        at = next((i for i, ln in enumerate(lines) if re.match(r"(import|from)\s", ln)), 0)
        lines.insert(at, header)
        with open(out_script, "w", encoding="utf-8") as f:
            f.write("".join(lines))
        arcpy.AddMessage("Cleaned copy: %s (%d path(s) made relative)" % (out_script, len(edits)))

    if out_table:
        folder, tname = os.path.split(out_table)
        if arcpy.Exists(out_table):
            arcpy.management.Delete(out_table)
        arcpy.management.CreateTable(folder, tname)
        for fname, ftype, flen in (("Line", "LONG", None), ("Path", "TEXT", 512), ("Path_Exists", "TEXT", 4),
                                   ("Relative", "TEXT", 512), ("Note", "TEXT", 255)):
            arcpy.management.AddField(out_table, fname, ftype, field_length=flen)
        with arcpy.da.InsertCursor(out_table, ["Line", "Path", "Path_Exists", "Relative", "Note"]) as cur:
            for r in rows:
                cur.insertRow([r["line"], r["path"], r["exists"], r["relative"], r["note"]])
    return dict(paths=rows, relative_count=len(edits), overwrite_false_lines=overwrite_false)


# ---------------------------------------------------------------------------
# A4  Check Script Tool Parameters
# ---------------------------------------------------------------------------
_PARAM_CALL = re.compile(r"\b(GetParameterAsText|GetParameter|SetParameterAsText|SetParameter)\s*\(\s*(\d+)\s*[,)]")


class CheckScriptToolParameters:
    """Lists the parameters of every script tool in a toolbox (.atbx) and
    checks them against the tool's script: every GetParameterAsText(n) /
    GetParameter(n) index exists, every input is read, and every derived
    output is set with SetParameterAsText(n) / SetParameter(n). Episode A4
    uses it on the Solar Screen All Counties script tool."""

    def __init__(self):
        self.label = "Check Script Tool Parameters"
        self.description = ("Lists the parameters of every script tool in a toolbox (.atbx) "
                            "and checks the parameter indexes used in each tool's script.")
        self.category = "Python Scripts"

    def getParameterInfo(self):
        in_toolbox = arcpy.Parameter(displayName="Input Toolbox (.atbx)", name="in_toolbox",
                                     datatype="DEFile", parameterType="Required", direction="Input")
        in_toolbox.filter.list = ["atbx"]
        out_report = arcpy.Parameter(displayName="Output Report (Markdown)", name="out_report",
                                     datatype="DEFile", parameterType="Optional", direction="Output")
        out_report.filter.list = ["md", "txt"]
        issues = arcpy.Parameter(displayName="Issues Found", name="issue_count",
                                 datatype="GPLong", parameterType="Derived", direction="Output")
        return [in_toolbox, out_report, issues]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        result = check_script_tool_parameters(parameters[0].valueAsText, parameters[1].valueAsText)
        parameters[2].value = result["issue_count"]
        return

    def postExecute(self, parameters):
        return


def _read_atbx(path):
    """toolbox.content plus each tool's tool.content and script (linked file
    or embedded) from an .atbx, which is a zip file."""
    import zipfile
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        tb = json.loads(z.read("toolbox.content").decode("utf-8-sig"))
        tools = []
        for toolset in tb.get("toolsets", {}).values():
            for t in toolset.get("tools", []):
                content = json.loads(z.read(t + ".tool/tool.content").decode("utf-8-sig"))
                script, script_path = None, None
                if t + ".tool/tool.script.execute.py" in names:
                    script, script_path = z.read(t + ".tool/tool.script.execute.py").decode("utf-8-sig"), "(embedded)"
                elif t + ".tool/tool.script.execute.link" in names:
                    link = z.read(t + ".tool/tool.script.execute.link").decode("utf-8-sig").strip()
                    # a relative link starts inside the toolbox: <atbx>\<tool>.tool\
                    script_path = link if os.path.isabs(link) else \
                        os.path.normpath(os.path.join(path, t + ".tool", link))
                    if os.path.exists(script_path):
                        with open(script_path, encoding="utf-8-sig") as f:
                            script = f.read()
                tools.append(dict(name=t, type=content.get("type", ""), content=content,
                                  script=script, script_path=script_path))
    return tb.get("alias", ""), tools


def check_script_tool_parameters(in_toolbox, out_report=None):
    """Core logic, callable from Python and from the tool. Returns a dict with
    one entry per tool (parameters and issues) and the total issue count."""
    alias, tools = _read_atbx(in_toolbox)
    imported = False
    try:
        arcpy.ImportToolbox(in_toolbox)
        imported = bool(alias)
    except Exception as e:  # the parameter list still comes from tool.content
        arcpy.AddWarning("Could not import the toolbox (%s); reading tool.content only." % e)
    report, total = [], 0
    for t in tools:
        params = []
        if imported:
            try:
                for i, p in enumerate(arcpy.GetParameterInfo("%s_%s" % (t["name"], alias))):
                    params.append(dict(i=i, name=p.name, label=p.displayName, type=p.parameterType,
                                       direction=p.direction, datatype=p.datatype))
            except Exception:
                params = []
        if not params:   # fallback: tool.content keeps the parameters in dialog order
            for i, (pname, p) in enumerate(t["content"].get("params", {}).items()):
                params.append(dict(i=i, name=pname, label=pname, type=p.get("type", "required").title(),
                                   direction=p.get("direction", "in").replace("in", "Input").replace("out", "Output"),
                                   datatype=p.get("datatype", {}).get("type", "")))
        issues = []
        if t["type"] != "ScriptTool":
            arcpy.AddMessage("%s: %s, %d parameter(s) (not a script tool, not checked)" % (t["name"], t["type"], len(params)))
        elif t["script"] is None:
            issues.append("script not found: %s" % t["script_path"])
        else:
            reads, sets = set(), set()
            for m in _PARAM_CALL.finditer(t["script"]):
                (sets if m.group(1).startswith("Set") else reads).add(int(m.group(2)))
            for n in sorted((reads | sets) - set(range(len(params)))):
                issues.append("the script uses index %d, but the tool has %d parameter(s) (0 to %d)" % (n, len(params), len(params) - 1))
            for p in params:
                derived = p["type"] == "Derived"
                if derived and p["direction"] == "Output" and p["i"] not in sets:
                    issues.append("derived output %d (%s) is never set with SetParameterAsText(%d)" % (p["i"], p["label"], p["i"]))
                if not derived and p["direction"] == "Input" and p["i"] not in reads:
                    issues.append("input %d (%s) is never read with GetParameterAsText(%d)" % (p["i"], p["label"], p["i"]))
        arcpy.AddMessage("%s (%s): %d parameter(s)" % (t["name"], t["script_path"] or "no script", len(params)))
        for p in params:
            arcpy.AddMessage("  %d  %s  [%s, %s, %s]" % (p["i"], p["label"], p["datatype"], p["direction"], p["type"]))
        for s in issues:
            arcpy.AddWarning("  %s: %s" % (t["name"], s))
        total += len(issues)
        report.append(dict(tool=t["name"], type=t["type"], script=t["script_path"], params=params, issues=issues))
    arcpy.AddMessage("%d tool(s), %d issue(s)." % (len(report), total))

    if out_report:
        lines = ["# Script tool parameters: %s" % os.path.basename(in_toolbox), ""]
        for r in report:
            lines += ["## %s" % r["tool"], "", "Script: %s" % (r["script"] or "-"), "",
                      "| Index | Label | Name | Data type | Direction | Type |", "|---|---|---|---|---|---|"]
            lines += ["| %d | %s | %s | %s | %s | %s |" % (p["i"], p["label"], p["name"], p["datatype"], p["direction"], p["type"])
                      for p in r["params"]]
            lines += [""] + (["Issues:"] + ["- " + s for s in r["issues"]] if r["issues"] else ["No issues."]) + [""]
        with open(out_report, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        arcpy.AddMessage("Report: %s" % out_report)
    return dict(tools=report, issue_count=total)


# ---------------------------------------------------------------------------
# A5  Export Features to Folder
# ---------------------------------------------------------------------------
EXPORT_FORMATS = ["GeoJSON", "Shapefile", "CSV", "File Geodatabase"]


class ExportFeaturesToFolder:
    """Exports a layer, or only the rows that match an SQL expression, to a
    folder as GeoJSON, a shapefile, a CSV table or a feature class in a file
    geodatabase. Episode A5 builds this tool line by line."""

    def __init__(self):
        self.label = "Export Features to Folder"
        self.description = ("Exports the features of a layer (all of them, or only those that "
                            "match an expression) to a folder as GeoJSON, a shapefile, a CSV "
                            "table or a feature class in a file geodatabase.")
        self.category = "Export"

    def getParameterInfo(self):
        in_features = arcpy.Parameter(
            displayName="Input Features", name="in_features",
            datatype="GPFeatureLayer", parameterType="Required", direction="Input")

        expression = arcpy.Parameter(
            displayName="Expression", name="where_clause",
            datatype="GPSQLExpression", parameterType="Optional", direction="Input")
        expression.parameterDependencies = [in_features.name]   # build it on the input fields

        out_folder = arcpy.Parameter(
            displayName="Output Folder", name="out_folder",
            datatype="DEFolder", parameterType="Required", direction="Input")

        out_format = arcpy.Parameter(
            displayName="Output Format", name="out_format",
            datatype="GPString", parameterType="Required", direction="Input")
        out_format.filter.type = "ValueList"
        out_format.filter.list = EXPORT_FORMATS
        out_format.value = "GeoJSON"

        out_name = arcpy.Parameter(
            displayName="Output Name", name="out_name",
            datatype="GPString", parameterType="Optional", direction="Input")

        out_path = arcpy.Parameter(
            displayName="Output", name="out_path",
            datatype="DEType", parameterType="Derived", direction="Output")

        return [in_features, expression, out_folder, out_format, out_name, out_path]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # Suggest an output name from the input the first time an input is chosen.
        in_features, out_name = parameters[0], parameters[4]
        if in_features.altered and in_features.value and not out_name.altered:
            out_name.value = arcpy.ValidateTableName(arcpy.Describe(in_features.value).baseName)
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        in_features = parameters[0].valueAsText
        where = parameters[1].valueAsText
        out_folder = parameters[2].valueAsText
        out_format = parameters[3].valueAsText
        out_name = parameters[4].valueAsText
        result = export_features(in_features, out_folder, out_format, where, out_name)
        parameters[5].value = result["output"]
        return

    def postExecute(self, parameters):
        return


def export_features(in_features, out_folder, out_format="GeoJSON", where=None, out_name=None):
    """Core logic, callable from Python and from the tool. Returns a dict with
    the output path, the number of features written and the seconds taken."""
    t0 = time.time()
    if out_format not in EXPORT_FORMATS:
        raise ValueError("Output Format must be one of %s" % ", ".join(EXPORT_FORMATS))
    base = out_name or arcpy.Describe(in_features).baseName
    base = arcpy.ValidateTableName(os.path.splitext(base)[0], out_folder)

    # One temporary layer holds only the matching rows, so every format exports the same subset.
    lyr = arcpy.management.MakeFeatureLayer(in_features, "ats_export_subset", where_clause=where)[0]
    try:
        count = int(arcpy.management.GetCount(lyr)[0])
        if count == 0:
            arcpy.AddWarning("The expression matches no features; the output will be empty.")
        arcpy.AddMessage("Exporting %d feature(s) as %s..." % (count, out_format))

        if out_format == "GeoJSON":
            out = os.path.join(out_folder, base + ".geojson")
            arcpy.conversion.FeaturesToJSON(lyr, out, geoJSON="GEOJSON", outputToWGS84="WGS84")
        elif out_format == "Shapefile":
            out = os.path.join(out_folder, base + ".shp")
            arcpy.conversion.ExportFeatures(lyr, out)
        elif out_format == "CSV":
            out = os.path.join(out_folder, base + ".csv")
            arcpy.conversion.ExportTable(lyr, out)
            arcpy.AddMessage("A CSV table holds the attributes only, not the shapes.")
        else:   # File Geodatabase
            gdb = os.path.join(out_folder, "Exports.gdb")
            if not arcpy.Exists(gdb):
                arcpy.management.CreateFileGDB(out_folder, "Exports.gdb")
            out = os.path.join(gdb, arcpy.ValidateTableName(base, gdb))
            arcpy.conversion.ExportFeatures(lyr, out)
    finally:
        arcpy.management.Delete(lyr)

    secs = round(time.time() - t0, 1)
    arcpy.AddMessage("Wrote %s (%d features, %.1f s)." % (out, count, secs))
    return dict(output=out, count=count, seconds=secs)


# ---------------------------------------------------------------------------
# A6  Export Pro Symbols to SVG/PNG
#     A "smart" tool dialog: value lists filled from the data, a list that
#     depends on another list, parameters that switch on and off, and an
#     optional parameter that becomes required for one choice.
# ---------------------------------------------------------------------------
SCOPE_ALL = "All point symbols"
SCOPE_CATEGORIES = "Selected categories"
SCOPE_SYMBOLS = "Selected symbols"
SYMBOL_SCOPES = [SCOPE_ALL, SCOPE_CATEGORIES, SCOPE_SYMBOLS]
SYMBOL_FORMATS = ["SVG", "PNG", "SVG and PNG"]
POINT_SYMBOL_CLASS = 3          # ITEMS.CLASS of a point symbol in a .stylx
NO_CATEGORY = "(no category)"
_STYLE_CACHE = {}               # validation runs on every change in the dialog: read each style once


class ExportProSymbols:
    """Exports the point symbols of an ArcGIS Pro style (.stylx) to SVG and/or
    PNG files, one file per symbol, in one subfolder per category.
    Episode A6 uses this tool to teach updateParameters and updateMessages."""

    def __init__(self):
        self.label = "Export Pro Symbols to SVG/PNG"
        self.description = ("Exports point symbols from an ArcGIS Pro style (.stylx) to SVG and/or PNG "
                            "files, one file per symbol in a subfolder per category: all point symbols, "
                            "the symbols in selected categories, or selected symbols.")
        self.category = "Symbology"

    def getParameterInfo(self):
        in_style = arcpy.Parameter(
            displayName="Input Style", name="in_style",
            datatype="DEFile", parameterType="Required", direction="Input")
        in_style.filter.list = ["stylx"]                 # File filter: only .stylx files

        scope = arcpy.Parameter(
            displayName="Export", name="scope",
            datatype="GPString", parameterType="Required", direction="Input")
        scope.filter.type = "ValueList"
        scope.filter.list = SYMBOL_SCOPES
        scope.value = SCOPE_ALL

        categories = arcpy.Parameter(
            displayName="Categories", name="categories",
            datatype="GPString", parameterType="Optional", direction="Input", multiValue=True)
        categories.filter.type = "ValueList"            # filled from the style in updateParameters

        symbols = arcpy.Parameter(
            displayName="Symbols", name="symbols",
            datatype="GPString", parameterType="Optional", direction="Input", multiValue=True)
        symbols.filter.type = "ValueList"               # filled from the style and the chosen categories

        out_folder = arcpy.Parameter(
            displayName="Output Folder", name="out_folder",
            datatype="DEFolder", parameterType="Required", direction="Input")

        out_format = arcpy.Parameter(
            displayName="Output Format", name="out_format",
            datatype="GPString", parameterType="Required", direction="Input")
        out_format.filter.type = "ValueList"
        out_format.filter.list = SYMBOL_FORMATS
        out_format.value = "SVG and PNG"

        png_size = arcpy.Parameter(
            displayName="PNG Size (pixels)", name="png_size",
            datatype="GPLong", parameterType="Optional", direction="Input")
        png_size.filter.type = "Range"
        png_size.filter.list = [16, 1024]
        png_size.value = 256

        # The derived output is the folder, not a list of files: geoprocessing writes a
        # metadata .xml next to every PNG it receives as a file output.
        out_location = arcpy.Parameter(
            displayName="Exported Folder", name="out_location",
            datatype="DEFolder", parameterType="Derived", direction="Output")

        return [in_style, scope, categories, symbols, out_folder, out_format, png_size, out_location]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        in_style, scope, categories, symbols, out_folder, out_format, png_size = parameters[:7]

        # 1. Switch parameters on and off from the other choices.
        categories.enabled = scope.valueAsText in (SCOPE_CATEGORIES, SCOPE_SYMBOLS)
        symbols.enabled = scope.valueAsText == SCOPE_SYMBOLS
        png_size.enabled = "PNG" in (out_format.valueAsText or "")

        # 2. Fill the value lists from the style the user picked.
        catalog = style_catalog_or_none(in_style.valueAsText)
        if not catalog:
            return                                       # updateMessages explains why
        category_list = sorted({c for c, n in catalog}, key=str.lower)
        categories.filter.list = category_list
        picked = [c for c in (categories.values or []) if c in category_list]
        if len(picked) != len(categories.values or []):
            categories.values = picked or None           # drop picks from a previous style

        # 3. The Symbols list depends on the Categories list.
        shown = set(picked) or set(category_list)
        symbol_list = [symbol_label(c, n) for c, n in catalog if c in shown]
        symbols.filter.list = symbol_list
        kept = [s for s in (symbols.values or []) if s in symbol_list]
        if len(kept) != len(symbols.values or []):
            symbols.values = kept or None
        return

    def updateMessages(self, parameters):
        in_style, scope, categories, symbols, out_folder = parameters[:5]

        # A style that cannot be read, or has no point symbols, is an error on the Input Style.
        if in_style.valueAsText and not in_style.hasError():
            try:
                if not read_style_catalog(in_style.valueAsText):
                    in_style.setErrorMessage("This style has no point symbols.")
            except ValueError as e:
                in_style.setErrorMessage(str(e))

        # Optional parameters that are required for one choice: message 735 = "Value is required".
        if scope.valueAsText == SCOPE_CATEGORIES and not categories.valueAsText:
            categories.setIDMessage("ERROR", 735, categories.displayName)
        if scope.valueAsText == SCOPE_SYMBOLS and not symbols.valueAsText:
            symbols.setIDMessage("ERROR", 735, symbols.displayName)

        # A warning does not stop the tool; it tells the user what will happen.
        if out_folder.valueAsText and os.path.isdir(out_folder.valueAsText) and os.listdir(out_folder.valueAsText):
            out_folder.setWarningMessage("The folder is not empty. Files with the same names are replaced.")
        return

    def execute(self, parameters, messages):
        result = export_style_symbols(
            parameters[0].valueAsText, parameters[4].valueAsText,
            scope=parameters[1].valueAsText,
            categories=list(parameters[2].values or []),
            symbols=list(parameters[3].values or []),
            out_format=parameters[5].valueAsText,
            png_size=int(parameters[6].value or 256))
        parameters[7].value = parameters[4].valueAsText
        return

    def postExecute(self, parameters):
        return


def _style_uri(stylx):
    # Read-only SQLite connection: exporting never changes the style.
    from urllib.request import pathname2url
    return "file:%s?mode=ro" % pathname2url(os.path.abspath(stylx))


def read_style_catalog(stylx):
    """[(category, name), ...] of the point symbols in a style. A .stylx file is an
    SQLite database; its ITEMS table holds one row per style item. Cached by path
    and modified time so dialog validation stays fast."""
    if not os.path.isfile(stylx):
        raise ValueError("The style file does not exist.")
    key = (os.path.normcase(os.path.abspath(stylx)), os.path.getmtime(stylx))
    if key not in _STYLE_CACHE:
        try:
            con = sqlite3.connect(_style_uri(stylx), uri=True)
            try:
                rows = con.execute("SELECT CATEGORY, NAME FROM ITEMS WHERE CLASS = ?",
                                   (POINT_SYMBOL_CLASS,)).fetchall()
            finally:
                con.close()
        except sqlite3.DatabaseError:
            raise ValueError("This file is not an ArcGIS Pro style that can be read "
                             "(system styles cannot be opened; use a copy of your own style).")
        catalog = sorted({((c or NO_CATEGORY), n) for c, n in rows if n},
                         key=lambda cn: (cn[0].lower(), cn[1].lower()))
        _STYLE_CACHE[key] = catalog
    return _STYLE_CACHE[key]


def style_catalog_or_none(stylx):
    try:
        return read_style_catalog(stylx) if stylx else None
    except ValueError:
        return None


def symbol_label(category, name):
    """How a symbol appears in the Symbols list: names repeat across categories."""
    return "%s (%s)" % (name, category)


def read_symbol(stylx, category, name):
    """The CIM definition (a dict) of one point symbol."""
    con = sqlite3.connect(_style_uri(stylx), uri=True)
    try:
        cat = "" if category == NO_CATEGORY else category
        row = con.execute("SELECT CONTENT FROM ITEMS WHERE CLASS = ? AND NAME = ? AND IFNULL(CATEGORY, '') = ?",
                          (POINT_SYMBOL_CLASS, name, cat)).fetchone()
    finally:
        con.close()
    if row is None:
        raise LookupError("No point symbol %s" % symbol_label(category, name))
    content = row[0].decode("utf-8") if isinstance(row[0], bytes) else row[0]
    return json.loads(content.lstrip("﻿").rstrip("\x00"))


def safe_file_name(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name).strip(" .") or "symbol"


# --- CIM geometry -> drawing commands -----------------------------------------------------------
# Every shape is a list of commands in points, y up: ("M", x, y), ("L", x, y),
# ("C", x1, y1, x2, y2, x, y) and ("Z",). Arcs become cubic Bezier curves, so the
# SVG writer and the PNG renderer draw exactly the same outline.

def _cim_color(color):
    """CIM color -> (r, g, b, alpha 0-1), or None."""
    if not color:
        return None
    v = list(color.get("values") or [])
    t = color.get("type")
    if t == "CIMRGBColor" and len(v) >= 3:
        rgb, a = v[:3], (v[3] if len(v) > 3 else 100)
    elif t == "CIMHSVColor" and len(v) >= 3:
        import colorsys
        rgb = [255 * x for x in colorsys.hsv_to_rgb(v[0] / 360.0, v[1] / 100.0, v[2] / 100.0)]
        a = v[3] if len(v) > 3 else 100
    elif t == "CIMCMYKColor" and len(v) >= 4:
        k = v[3] / 100.0
        rgb = [255 * (1 - x / 100.0) * (1 - k) for x in v[:3]]
        a = v[4] if len(v) > 4 else 100
    elif t == "CIMGrayColor" and v:
        rgb, a = [v[0]] * 3, (v[1] if len(v) > 1 else 100)
    else:
        return None
    return (int(round(rgb[0])), int(round(rgb[1])), int(round(rgb[2])), max(0.0, min(1.0, a / 100.0)))


def _arc_curves(center, radius, a0, sweep, to_world):
    """Split an arc (radians) into Bezier curves of at most 90 degrees."""
    n = max(1, int(math.ceil(abs(sweep) / (math.pi / 2) - 1e-9)))
    step = sweep / n
    k = 4.0 / 3.0 * math.tan(step / 4.0)
    out = []
    for i in range(n):
        t0, t1 = a0 + i * step, a0 + (i + 1) * step
        p0 = (center[0] + radius * math.cos(t0), center[1] + radius * math.sin(t0))
        p3 = (center[0] + radius * math.cos(t1), center[1] + radius * math.sin(t1))
        c1 = (p0[0] - k * radius * math.sin(t0), p0[1] + k * radius * math.cos(t0))
        c2 = (p3[0] + k * radius * math.sin(t1), p3[1] - k * radius * math.cos(t1))
        (x1, y1), (x2, y2), (x3, y3) = to_world(c1), to_world(c2), to_world(p3)
        out.append(("C", x1, y1, x2, y2, x3, y3))
    return out


def _same_point(p, q):
    return abs(p[0] - q[0]) < 1e-9 and abs(p[1] - q[1]) < 1e-9


def _elliptic_arc(start, seg):
    """{"a": [end, center, minor, clockwise, (rotation, semi-major axis, ratio)]}."""
    end, center = seg[0], seg[1]
    clockwise = len(seg) > 3 and bool(seg[3])
    rot = seg[4] if len(seg) > 4 else 0.0
    ratio = seg[6] if len(seg) > 6 and seg[6] else 1.0
    cr, sr = math.cos(rot), math.sin(rot)

    def to_local(p):
        dx, dy = p[0] - center[0], p[1] - center[1]
        return (dx * cr + dy * sr, (-dx * sr + dy * cr) / ratio)

    def to_world(p):
        x, y = p[0], p[1] * ratio
        return (center[0] + x * cr - y * sr, center[1] + x * sr + y * cr)

    s, e = to_local(start), to_local(end)
    radius = math.hypot(*s)
    a0, a1 = math.atan2(s[1], s[0]), math.atan2(e[1], e[0])
    if _same_point(start, end):
        sweep = -2 * math.pi if clockwise else 2 * math.pi       # a full circle / ellipse
    else:
        ccw = (a1 - a0) % (2 * math.pi)
        sweep = ccw - 2 * math.pi if clockwise else ccw
    return _arc_curves((0.0, 0.0), radius, a0, sweep, to_world)


def _circular_arc(start, seg):
    """{"c": [end, a point on the arc]}: the circle through three points."""
    end, mid = seg[0], seg[1]
    (ax, ay), (bx, by), (cx, cy) = start, mid, end
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return [("L", end[0], end[1])]                           # straight after all
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    radius = math.hypot(ax - ux, ay - uy)
    a0 = math.atan2(ay - uy, ax - ux)
    am = (math.atan2(by - uy, bx - ux) - a0) % (2 * math.pi)
    a1 = (math.atan2(cy - uy, cx - ux) - a0) % (2 * math.pi)
    sweep = a1 if am < a1 else a1 - 2 * math.pi
    return _arc_curves((ux, uy), radius, a0, sweep, lambda p: p)


def _parts_to_commands(parts, closed):
    cmds = []
    for part in parts or []:
        if not part:
            continue
        cur = part[0]
        cmds.append(("M", cur[0], cur[1]))
        for seg in part[1:]:
            if isinstance(seg, dict):
                if "b" in seg:                                    # cubic Bezier: end, control 1, control 2
                    e, c1, c2 = seg["b"]
                    cmds.append(("C", c1[0], c1[1], c2[0], c2[1], e[0], e[1]))
                    cur = e
                elif "a" in seg:
                    cmds += _elliptic_arc(cur, seg["a"]); cur = seg["a"][0]
                elif "c" in seg:
                    cmds += _circular_arc(cur, seg["c"]); cur = seg["c"][0]
                else:                                             # unknown curve: straight line to its end
                    cur = list(seg.values())[0][0]
                    cmds.append(("L", cur[0], cur[1]))
            else:
                cur = seg
                cmds.append(("L", cur[0], cur[1]))
        if closed:
            cmds.append(("Z",))
    return cmds


def _transform(cmds, f):
    out = []
    for c in cmds:
        if c[0] == "Z":
            out.append(c)
        else:
            xy = [v for i in range(1, len(c), 2) for v in f(c[i], c[i + 1])]
            out.append((c[0],) + tuple(xy))
    return out


def symbol_to_shapes(cim):
    """Turn a CIMPointSymbol into drawable shapes (bottom first) and a list of notes
    about anything that could not be drawn (font glyph markers, effects...)."""
    shapes, notes = [], []
    if cim.get("type") != "CIMPointSymbol":
        return shapes, ["not a point symbol (%s)" % cim.get("type")]
    for layer in reversed(cim.get("symbolLayers") or []):         # the first layer is drawn on top
        if not layer.get("enable", True):
            continue
        kind = layer.get("type")
        size = float(layer.get("size") or 10.0)
        ox, oy = float(layer.get("offsetX") or 0.0), float(layer.get("offsetY") or 0.0)
        rot = math.radians(float(layer.get("rotation") or 0.0))
        if kind == "CIMVectorMarker":
            fr = layer.get("frame") or {"xmin": -size / 2, "ymin": -size / 2, "xmax": size / 2, "ymax": size / 2}
            fw, fh = fr["xmax"] - fr["xmin"], fr["ymax"] - fr["ymin"]
            scale = size / (fh or fw or size)                    # the marker size is the frame height
            fcx, fcy = (fr["xmin"] + fr["xmax"]) / 2.0, (fr["ymin"] + fr["ymax"]) / 2.0
            anchor = layer.get("anchorPoint") or {}
            ax, ay = float(anchor.get("x") or 0.0), float(anchor.get("y") or 0.0)
            if layer.get("anchorPointUnits") == "Relative":
                ax, ay = ax * fw * scale, ay * fh * scale
            stroke_scale = scale if layer.get("scaleSymbolsProportionally") else 1.0

            def place(x, y, scale=scale, fcx=fcx, fcy=fcy, ax=ax, ay=ay, ox=ox, oy=oy, rot=rot):
                x, y = (x - fcx) * scale - ax, (y - fcy) * scale - ay
                if rot:
                    x, y = x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)
                return x + ox, y + oy

            for graphic in layer.get("markerGraphics") or []:
                geom, sym = graphic.get("geometry") or {}, graphic.get("symbol") or {}
                if "rings" in geom or "curveRings" in geom:
                    cmds = _parts_to_commands(geom.get("curveRings") or geom.get("rings"), True)
                elif "paths" in geom or "curvePaths" in geom:
                    cmds = _parts_to_commands(geom.get("curvePaths") or geom.get("paths"), False)
                else:
                    notes.append("a %s graphic was skipped" % sym.get("type", "point"))
                    continue
                cmds = _transform(cmds, place)
                for sl in reversed(sym.get("symbolLayers") or []):
                    if not sl.get("enable", True):
                        continue
                    t = sl.get("type")
                    if t == "CIMSolidFill" and "Z" in [c[0] for c in cmds]:
                        col = _cim_color(sl.get("color"))
                        if col and col[3] > 0:
                            shapes.append(dict(kind="path", cmds=cmds, fill=col, stroke=None, width=0))
                    elif t == "CIMSolidStroke":
                        col, w = _cim_color(sl.get("color")), float(sl.get("width") or 0) * stroke_scale
                        if col and col[3] > 0 and w > 0:          # width 0 = hairline, left out
                            shapes.append(dict(kind="path", cmds=cmds, fill=None, stroke=col, width=w))
                    else:
                        notes.append("%s layer skipped" % t)
        elif kind == "CIMPictureMarker":
            url = layer.get("url") or ""
            m = re.match(r"data:(image/[\w.+-]+);base64,(.*)$", url, re.S)
            if not m:
                notes.append("picture marker without embedded image skipped")
                continue
            import base64
            shapes.append(dict(kind="image", mime=m.group(1), data=base64.b64decode(m.group(2)),
                               box=(ox - size / 2.0, oy - size / 2.0, size)))
        else:
            notes.append("%s layer skipped (font glyphs and 3D models are not drawn)" % kind)
    return shapes, notes


def _shapes_bounds(shapes):
    xs, ys = [], []
    for s in shapes:
        if s["kind"] == "image":
            x0, y0, w = s["box"]
            xs += [x0, x0 + w]; ys += [y0, y0 + w]
            continue
        pad = s["width"] / 2.0
        for c in s["cmds"]:
            for i in range(1, len(c), 2):
                xs += [c[i] - pad, c[i] + pad]; ys += [c[i + 1] - pad, c[i + 1] + pad]
    side = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.04 or 1.0   # square, 2 % margin each side
    cx, cy = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
    return cx - side / 2.0, cy - side / 2.0, side


def shapes_to_svg(shapes, size_px=256):
    """A square SVG; y is flipped because SVG counts down from the top."""
    x0, y0, side = _shapes_bounds(shapes)
    top = y0 + side
    body = []
    for s in shapes:
        if s["kind"] == "image":
            import base64
            ix, iy, w = s["box"]
            body.append('<image x="%.4f" y="%.4f" width="%.4f" height="%.4f" href="data:%s;base64,%s"/>'
                        % (ix - x0, top - (iy + w), w, w, s["mime"], base64.b64encode(s["data"]).decode("ascii")))
            continue
        d = []
        for c in s["cmds"]:
            if c[0] == "Z":
                d.append("Z")
            else:
                d.append(c[0] + " ".join("%.4f %.4f" % (c[i] - x0, top - c[i + 1]) for i in range(1, len(c), 2)))
        attrs = []
        if s["fill"]:
            r, g, b, a = s["fill"]
            attrs.append('fill="rgb(%d,%d,%d)" fill-rule="evenodd"' % (r, g, b) + (' fill-opacity="%.3f"' % a if a < 1 else ""))
        else:
            attrs.append('fill="none"')
        if s["stroke"]:
            r, g, b, a = s["stroke"]
            attrs.append('stroke="rgb(%d,%d,%d)" stroke-width="%.4f" stroke-linejoin="round" stroke-linecap="round"'
                         % (r, g, b, s["width"]) + (' stroke-opacity="%.3f"' % a if a < 1 else ""))
        body.append('<path d="%s" %s/>' % (" ".join(d), " ".join(attrs)))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %.4f %.4f">\n%s\n</svg>\n'
            % (size_px, size_px, side, side, "\n".join(body)))


def shapes_to_png(shapes, png_path, size_px=256):
    """Draw the same shapes with matplotlib (ships with ArcGIS Pro) on a transparent square."""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    x0, y0, side = _shapes_bounds(shapes)
    fig = Figure(figsize=(size_px / 100.0, size_px / 100.0), dpi=100)
    canvas = FigureCanvasAgg(fig)
    fig.patch.set_alpha(0)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x0 + side); ax.set_ylim(y0, y0 + side); ax.axis("off")
    pt_to_lw = size_px / side * 72.0 / 100.0                # stroke width in points -> matplotlib line width
    code = {"M": Path.MOVETO, "L": Path.LINETO, "C": Path.CURVE4}
    for s in shapes:
        if s["kind"] == "image":
            if s["mime"] in ("image/png", "image/jpeg", "image/bmp", "image/gif"):
                import io
                from PIL import Image
                ix, iy, w = s["box"]
                ax.imshow(Image.open(io.BytesIO(s["data"])).convert("RGBA"), extent=(ix, ix + w, iy, iy + w))
                ax.set_xlim(x0, x0 + side); ax.set_ylim(y0, y0 + side)
            continue
        verts, codes, first = [], [], None
        for c in s["cmds"]:
            if c[0] == "Z":
                verts.append(first); codes.append(Path.CLOSEPOLY)
                continue
            pts = [(c[i], c[i + 1]) for i in range(1, len(c), 2)]
            if c[0] == "M":
                first = pts[0]
            verts += pts; codes += [code[c[0]]] * len(pts)
        fc = tuple(v / 255.0 for v in s["fill"][:3]) + (s["fill"][3],) if s["fill"] else "none"
        ec = tuple(v / 255.0 for v in s["stroke"][:3]) + (s["stroke"][3],) if s["stroke"] else "none"
        ax.add_patch(PathPatch(Path(verts, codes), facecolor=fc, edgecolor=ec,
                               linewidth=s["width"] * pt_to_lw if s["stroke"] else 0,
                               joinstyle="round", capstyle="round"))
    canvas.print_png(png_path)


def export_style_symbols(stylx, out_folder, scope=SCOPE_ALL, categories=None, symbols=None,
                         out_format="SVG and PNG", png_size=256):
    """Core logic, callable from Python and from the tool. Returns a dict with the
    files written, the symbols exported and skipped, and the seconds taken."""
    t0 = time.time()
    if scope not in SYMBOL_SCOPES:
        raise ValueError("Export must be one of %s" % ", ".join(SYMBOL_SCOPES))
    if out_format not in SYMBOL_FORMATS:
        raise ValueError("Output Format must be one of %s" % ", ".join(SYMBOL_FORMATS))
    catalog = read_style_catalog(stylx)
    if scope == SCOPE_CATEGORIES:
        wanted = set(categories or [])
        todo = [(c, n) for c, n in catalog if c in wanted]
    elif scope == SCOPE_SYMBOLS:
        wanted = set(symbols or [])
        todo = [(c, n) for c, n in catalog if symbol_label(c, n) in wanted]
    else:
        todo = list(catalog)
    if not todo:
        arcpy.AddWarning("Nothing to export: no point symbols match the choices.")
    write_svg, write_png = "SVG" in out_format, "PNG" in out_format
    arcpy.AddMessage("Exporting %d symbol(s) as %s..." % (len(todo), out_format))
    arcpy.SetProgressor("step", "Exporting symbols...", 0, max(len(todo), 1), 1)
    files, exported, skipped = [], 0, 0
    for category, name in todo:
        arcpy.SetProgressorLabel(symbol_label(category, name))
        shapes, notes = symbol_to_shapes(read_symbol(stylx, category, name))
        for note in notes:
            arcpy.AddWarning("%s: %s." % (symbol_label(category, name), note))
        if not shapes:
            skipped += 1
            arcpy.SetProgressorPosition()
            continue
        folder = os.path.join(out_folder, safe_file_name(category))
        os.makedirs(folder, exist_ok=True)
        base = os.path.join(folder, safe_file_name(name))
        if write_svg:
            with open(base + ".svg", "w", encoding="utf-8") as f:
                f.write(shapes_to_svg(shapes, png_size))
            files.append(base + ".svg")
        if write_png:
            shapes_to_png(shapes, base + ".png", png_size)
            files.append(base + ".png")
        exported += 1
        arcpy.SetProgressorPosition()
    arcpy.ResetProgressor()
    secs = round(time.time() - t0, 1)
    arcpy.AddMessage("Exported %d symbol(s), %d file(s), %d skipped, in %.1f s." % (exported, len(files), skipped, secs))
    return dict(files=files, exported=exported, skipped=skipped, seconds=secs)


# ---------------------------------------------------------------------------
# A7  ArcGIS Online from ArcGIS Pro (ArcGIS API for Python in a .pyt)
#     Describe Feature Services: a CSV report of the hosted feature layers you own.
#     Generate Branded Thumbnails: one 600 x 400 PNG per item, uploaded only when
#     you check the box. Sign-in comes from ArcGIS Pro, GIS("pro"): no user name,
#     password or token in the code. Both tools only read or change items you own.
# ---------------------------------------------------------------------------
ALL_FOLDERS = "(all my folders)"
ROOT_FOLDER = "(root folder)"
REPORT_COLUMNS = ["item_title", "item_id", "sharing", "layer", "geometry", "features",
                  "fields", "editable", "modified", "size_kb", "thumbnail"]
THUMB_SIZE = (600, 400)                 # ArcGIS Online item thumbnail: 600 x 400 pixels
THUMB_COLORS = {"Navy": ((19, 41, 75), (242, 140, 40)),      # background, accent
                "Charcoal": ((38, 41, 46), (0, 169, 157)),
                "Forest": ((24, 61, 45), (240, 195, 60))}
_PORTAL = {}                            # validation runs often: sign in and read folders once


def connect_active_portal():
    """The portal ArcGIS Pro is signed in to. Imported here, so the other tools load
    even where the ArcGIS API for Python is not installed."""
    if "gis" not in _PORTAL:
        from arcgis.gis import GIS
        _PORTAL["gis"] = GIS("pro")
    return _PORTAL["gis"]


def my_folder_names(gis):
    """Folder names of the signed-in user, for the Folder value list."""
    return [ALL_FOLDERS, ROOT_FOLDER] + sorted((f.name for f in gis.users.me.folders), key=str.lower)


def folder_choices_or_error():
    """(value list, None) or (None, message) - used by updateParameters / updateMessages."""
    if "folders" not in _PORTAL:
        try:
            _PORTAL["folders"] = (my_folder_names(connect_active_portal()), None)
        except Exception as e:      # not signed in, offline, no ArcGIS API for Python
            _PORTAL["folders"] = (None, "Sign in to ArcGIS Online in ArcGIS Pro first (%s)." % type(e).__name__)
    return _PORTAL["folders"]


def find_my_feature_services(gis, folder=None, tag=None, max_items=1000):
    """Hosted feature layer items (type Feature Service) owned by the signed-in user,
    optionally only one folder and only items with one tag (not case sensitive)."""
    me = gis.users.me
    if folder and folder not in (ALL_FOLDERS, ROOT_FOLDER):
        match = [f for f in me.folders if f.name == folder]
        if not match:
            raise ValueError("You have no folder named %s." % folder)
        items = list(match[0].list(item_type="Feature Service"))
    else:
        query = "owner:%s" % me.username
        if tag:
            query += ' AND tags:"%s"' % tag.replace('"', "")          # narrow the search on the portal
        items = gis.content.search(query, item_type="Feature Service", max_items=max_items)
        if folder == ROOT_FOLDER:
            items = [i for i in items if not i.ownerFolder]
    if tag:
        items = [i for i in items if tag.lower() in [t.lower() for t in (i.tags or [])]]
    items = [i for i in items if i.owner == me.username]        # never touch anyone else's item
    return sorted(items, key=lambda i: i.title.lower())


def _sharing(item):
    try:
        return item.sharing.sharing_level.name.lower()            # ArcGIS API for Python 2.4
    except Exception:
        return getattr(item, "access", "") or ""


def describe_item(item):
    """One report row per layer and table of a feature service item. Folder names are not
    written: a report shown on screen must not reveal how the account is organized."""
    base = dict(item_title=item.title, item_id=item.id,
                sharing=_sharing(item),
                modified=time.strftime("%Y-%m-%d", time.localtime(item.modified / 1000.0)),
                size_kb=int(round((item.size or 0) / 1024.0)), thumbnail="yes" if item.thumbnail else "no")
    rows = []
    for lyr in list(item.layers or []) + list(item.tables or []):
        p = lyr.properties
        geom = (p.get("geometryType") or "table").replace("esriGeometry", "")
        n = lyr.query(where="1=1", return_count_only=True)
        caps = p.get("capabilities") or ""                         # e.g. "Query" or "Create,Delete,Query,Update,Editing"
        editable = "yes" if any(c in caps for c in ("Create", "Update", "Delete")) else "no"
        rows.append(dict(base, layer=p.get("name"), geometry=geom, features=int(n),
                         fields=len(p.get("fields") or []), editable=editable))
    return rows


def describe_feature_services(gis, out_csv, folder=None, tag=None):
    """Core logic of Describe Feature Services. Writes the CSV report and returns
    a dict with the rows and totals."""
    t0 = time.time()
    items = find_my_feature_services(gis, folder, tag)
    arcpy.AddMessage("Found %d feature service(s) you own." % len(items))
    if not items:
        arcpy.AddWarning("No feature service matches the folder and tag.")
    rows = []
    arcpy.SetProgressor("step", "Describing feature services...", 0, max(len(items), 1), 1)
    for item in items:
        arcpy.SetProgressorLabel("Describing %s..." % item.title)
        r = describe_item(item)
        rows.extend(r)
        arcpy.AddMessage("%s: %d layer(s), %d feature(s), %s" % (
            item.title, len(r), sum(x["features"] for x in r), r[0]["sharing"] if r else _sharing(item)))
        arcpy.SetProgressorPosition()
    arcpy.ResetProgressor()
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=REPORT_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    total = sum(r["features"] for r in rows)
    secs = round(time.time() - t0, 1)
    arcpy.AddMessage("Wrote %s: %d service(s), %d layer(s), %d feature(s), %.1f s." % (
        os.path.basename(out_csv), len(items), len(rows), total, secs))
    return dict(rows=rows, services=len(items), layers=len(rows), features=total, seconds=secs, output=out_csv)


def _font(size, bold=True):
    from PIL import ImageFont
    for name in (("segoeuib.ttf", "arialbd.ttf") if bold else ("segoeui.ttf", "arial.ttf")):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


def _wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split():
        test = (line + " " + word).strip()
        if draw.textlength(test, font=font) <= width or not line:
            line = test
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


def render_thumbnail(title, detail, out_png, footer="All Things Spatial", geometry="", colors="Navy",
                     kind="FEATURE LAYER"):
    """Draws one branded 600 x 400 PNG: item kind, title (fitted, at most three
    lines), a detail line, a geometry glyph and a footer. Returns the PNG path."""
    from PIL import Image, ImageDraw
    bg, accent = THUMB_COLORS.get(colors, THUMB_COLORS["Navy"])
    W, H = THUMB_SIZE
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 10], fill=accent)                          # accent band
    d.text((36, 40), kind.upper(), font=_font(22), fill=accent)
    for size in (52, 46, 40, 34, 30):                                  # largest size that fits 3 lines
        font = _font(size)
        lines = _wrap(d, title, font, W - 72 - 120)
        if len(lines) <= 3:
            break
    if len(lines) > 3:                                                  # still too long: cut and mark it
        lines = lines[:3]
        while lines[2] and d.textlength(lines[2] + "...", font=font) > W - 72 - 120:
            lines[2] = lines[2].rsplit(" ", 1)[0] if " " in lines[2] else lines[2][:-1]
        lines[2] += "..."
    y = 84
    for ln in lines:
        d.text((36, y), ln, font=font, fill=(255, 255, 255))
        y += int(size * 1.18)
    d.text((36, y + 14), detail, font=_font(24, bold=False), fill=(214, 222, 232))
    gx, gy = W - 140, 70                                               # geometry glyph, top right
    g = (geometry or "").lower()
    if "polygon" in g:
        d.polygon([(gx + 10, gy + 70), (gx + 30, gy + 12), (gx + 92, gy + 24), (gx + 100, gy + 84), (gx + 44, gy + 96)],
                  outline=accent, width=6)
    elif "line" in g:
        d.line([(gx + 6, gy + 90), (gx + 40, gy + 40), (gx + 66, gy + 64), (gx + 100, gy + 10)], fill=accent, width=8,
               joint="curve")
    elif "point" in g:
        for px, py in ((gx + 20, gy + 70), (gx + 56, gy + 28), (gx + 92, gy + 78)):
            d.ellipse([px - 11, py - 11, px + 11, py + 11], fill=accent)
    d.line([(36, H - 70), (W - 36, H - 70)], fill=(255, 255, 255), width=1)
    d.text((36, H - 54), footer, font=_font(24), fill=(255, 255, 255))
    img.save(out_png, "PNG")
    return out_png


def generate_branded_thumbnails(gis, out_folder, folder=None, tag=None, footer="All Things Spatial",
                                colors="Navy", update=False):
    """Core logic of Generate Branded Thumbnails. Always writes the PNGs; replaces
    the item thumbnails on the portal only when update is True."""
    t0 = time.time()
    items = find_my_feature_services(gis, folder, tag)
    arcpy.AddMessage("Found %d feature service(s) you own." % len(items))
    if not items:
        arcpy.AddWarning("No feature service matches the folder and tag.")
    pngs, updated = [], 0
    arcpy.SetProgressor("step", "Drawing thumbnails...", 0, max(len(items), 1), 1)
    for item in items:
        arcpy.SetProgressorLabel("Drawing %s..." % item.title)
        rows = describe_item(item)
        geoms = sorted({r["geometry"] for r in rows})
        detail = "%d layer%s | %s features" % (len(rows), "" if len(rows) == 1 else "s",
                                                "{:,}".format(sum(r["features"] for r in rows)))
        png = os.path.join(out_folder, safe_file_name(item.title) + ".png")
        render_thumbnail(item.title, detail, png, footer, geoms[0] if len(geoms) == 1 else "", colors)
        pngs.append(png)
        if update:
            ok = item.update(thumbnail=png)
            if ok:
                updated += 1
                arcpy.AddMessage("%s: thumbnail updated." % item.title)
            else:
                arcpy.AddWarning("%s: the portal did not accept the thumbnail." % item.title)
        else:
            arcpy.AddMessage("%s: %s written (preview only)." % (item.title, os.path.basename(png)))
        arcpy.SetProgressorPosition()
    arcpy.ResetProgressor()
    secs = round(time.time() - t0, 1)
    arcpy.AddMessage("%d thumbnail(s) drawn, %d updated on the portal, %.1f s." % (len(pngs), updated, secs))
    return dict(pngs=pngs, updated=updated, services=len(items), seconds=secs)


def _agol_folder_and_tag_params():
    folder = arcpy.Parameter(displayName="Folder", name="folder", datatype="GPString",
                             parameterType="Optional", direction="Input")
    folder.filter.type = "ValueList"
    folder.filter.list = [ALL_FOLDERS]              # filled from your account in updateParameters
    folder.value = ALL_FOLDERS
    tag = arcpy.Parameter(displayName="Tag", name="tag", datatype="GPString",
                          parameterType="Optional", direction="Input")
    return folder, tag


def _fill_folder_list(folder_param):
    choices, _ = folder_choices_or_error()
    if choices:
        folder_param.filter.list = choices


def _portal_message(folder_param):
    _, err = folder_choices_or_error()
    if err:
        folder_param.setErrorMessage(err)


class DescribeFeatureServices:
    """Writes a CSV report of the hosted feature layers you own on ArcGIS Online:
    one row per layer with its geometry, feature count, fields, sharing and date.
    Episode A7 builds this tool."""

    def __init__(self):
        self.label = "Describe Feature Services"
        self.description = ("Writes a CSV report of the hosted feature layers you own in the portal "
                            "ArcGIS Pro is signed in to: one row per layer with its geometry type, "
                            "number of features, number of fields, sharing level and last change.")
        self.category = "ArcGIS Online"

    def getParameterInfo(self):
        folder, tag = _agol_folder_and_tag_params()
        out_csv = arcpy.Parameter(displayName="Output Report", name="out_csv", datatype="DEFile",
                                  parameterType="Required", direction="Output")
        out_csv.filter.list = ["csv"]
        count = arcpy.Parameter(displayName="Feature Services", name="service_count", datatype="GPLong",
                                parameterType="Derived", direction="Output")
        return [folder, tag, out_csv, count]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        _fill_folder_list(parameters[0])
        return

    def updateMessages(self, parameters):
        _portal_message(parameters[0])
        return

    def execute(self, parameters, messages):
        gis = connect_active_portal()
        result = describe_feature_services(gis, parameters[2].valueAsText,
                                           parameters[0].valueAsText, parameters[1].valueAsText)
        parameters[3].value = result["services"]
        return

    def postExecute(self, parameters):
        return


class GenerateBrandedThumbnails:
    """Draws a branded 600 x 400 thumbnail for each hosted feature layer you own
    and, when Update Thumbnails is checked, replaces the item thumbnail on
    ArcGIS Online. Episode A7 builds this tool."""

    def __init__(self):
        self.label = "Generate Branded Thumbnails"
        self.description = ("Draws a 600 x 400 PNG thumbnail (title, layer and feature count, footer) "
                            "for each hosted feature layer you own and, only when Update Thumbnails is "
                            "checked, replaces the item thumbnail in the portal ArcGIS Pro is signed in to.")
        self.category = "ArcGIS Online"

    def getParameterInfo(self):
        folder, tag = _agol_folder_and_tag_params()
        out_folder = arcpy.Parameter(displayName="Output Folder", name="out_folder", datatype="DEFolder",
                                     parameterType="Required", direction="Input")
        footer = arcpy.Parameter(displayName="Footer Text", name="footer", datatype="GPString",
                                 parameterType="Optional", direction="Input")
        footer.value = "All Things Spatial"
        colors = arcpy.Parameter(displayName="Colors", name="colors", datatype="GPString",
                                 parameterType="Optional", direction="Input")
        colors.filter.type = "ValueList"
        colors.filter.list = list(THUMB_COLORS)
        colors.value = "Navy"
        update = arcpy.Parameter(displayName="Update Thumbnails on the Portal", name="update_items",
                                 datatype="GPBoolean", parameterType="Optional", direction="Input")
        update.value = False                        # preview first: PNGs only
        count = arcpy.Parameter(displayName="Thumbnails Updated", name="updated_count", datatype="GPLong",
                                parameterType="Derived", direction="Output")
        return [folder, tag, out_folder, footer, colors, update, count]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        _fill_folder_list(parameters[0])
        return

    def updateMessages(self, parameters):
        _portal_message(parameters[0])
        if parameters[5].value:
            parameters[5].setWarningMessage("Checked: the tool replaces the thumbnail of every matching item you own.")
        return

    def execute(self, parameters, messages):
        gis = connect_active_portal()
        result = generate_branded_thumbnails(
            gis, parameters[2].valueAsText, parameters[0].valueAsText, parameters[1].valueAsText,
            parameters[3].valueAsText or "", parameters[4].valueAsText or "Navy", bool(parameters[5].value))
        parameters[6].value = result["updated"]
        return

    def postExecute(self, parameters):
        return


# ---------------------------------------------------------------------------
# Episode A8: Check Schedule Readiness (run it before Run > Schedule)
# ---------------------------------------------------------------------------
READY, WARN, FAIL = "PASS", "WARN", "FAIL"
TIME_STAMP = "%t%"          # inline variable: replaced by the run date and time, e.g. Report_20261118020000.csv

# Runs in a NEW Python process, the way a scheduled tool runs (outside ArcGIS Pro). It writes one word to
# the result file and never prints the user name, the portal URL or a token.
_SIGNIN_PROBE = r'''
import sys
out = sys.argv[1]
try:
    import arcpy
    from arcgis.gis import GIS
    me = GIS("pro").users.me
    word = "SIGNED_IN" if me is not None else "ANONYMOUS"
except Exception as e:
    word = "ERROR " + type(e).__name__
with open(out, "w", encoding="utf-8") as f:
    f.write(word)
'''


def _python_for_scheduled_runs():
    """pythonw.exe of the active ArcGIS Pro Python environment (python.exe if pythonw is missing)."""
    import sys
    for name in ("pythonw.exe", "python.exe"):
        p = os.path.join(sys.prefix, name)
        if os.path.exists(p):
            return p
    return sys.executable


def test_signin_outside_pro(timeout=180):
    """(status, note, seconds). Starts a separate Python process with no window, like a scheduled
    run, and connects with GIS("pro"). It works only if ArcGIS Pro stored the sign-in
    ("Sign in automatically") - the same thing a scheduled tool needs."""
    import subprocess, tempfile
    t0 = time.time()
    tmp = tempfile.mkdtemp(prefix="ats_signin_")
    probe, out = os.path.join(tmp, "probe.py"), os.path.join(tmp, "result.txt")
    with open(probe, "w", encoding="utf-8") as f:
        f.write(_SIGNIN_PROBE)
    try:
        subprocess.run([_python_for_scheduled_runs(), probe, out], timeout=timeout,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        word = open(out, encoding="utf-8").read().strip() if os.path.exists(out) else "ERROR no result"
    except subprocess.TimeoutExpired:
        word = "ERROR timeout"
    finally:
        for p in (probe, out):          # our own two temporary files
            if os.path.exists(p):
                os.remove(p)
        os.rmdir(tmp)
    secs = round(time.time() - t0, 1)
    if word == "SIGNED_IN":
        return READY, "A new Python process outside ArcGIS Pro signed in to your portal (%.0f s)." % secs, secs
    if word == "ANONYMOUS":
        return FAIL, ("A new Python process connected anonymously: turn on Sign in automatically "
                      "when you sign in to ArcGIS Pro."), secs
    return FAIL, ("A new Python process could not sign in (%s): sign in to ArcGIS Pro with "
                  "Sign in automatically checked, then run this check again." % word.replace("ERROR ", "")), secs


def _resolved_time_stamp(name, minutes=10):
    """The 14-digit date and time that %t% became in this run (yyyymmddhhmmss, within a few
    minutes of now), or None. Geoprocessing replaces %t% before the tool sees its values."""
    import datetime
    for m in re.finditer(r"(?<!\d)(\d{14})(?!\d)", name):
        try:
            when = datetime.datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
        except ValueError:
            continue
        if abs((datetime.datetime.now() - when).total_seconds()) <= minutes * 60:
            return m.group(1)
    return None


def check_output_location(out_path):
    """(status, note) for one output file or folder of the tool you will schedule."""
    if not out_path:
        return WARN, "No output given."
    folder = out_path if os.path.isdir(out_path) else os.path.dirname(out_path)
    if not os.path.isabs(out_path):
        return FAIL, "%s is not a full path: a scheduled run needs the full path." % out_path
    if not os.path.isdir(folder):
        return FAIL, "The folder %s does not exist." % folder
    import tempfile
    try:
        with tempfile.TemporaryFile(dir=folder):      # removed again when closed
            pass
    except OSError:
        return FAIL, "Cannot write to %s." % folder
    name = os.path.basename(out_path)
    if TIME_STAMP in name:
        return READY, "%s gets a new name every run (%s = date and time)." % (name, TIME_STAMP)
    if _resolved_time_stamp(name):      # run through the tool dialog, %t% is already replaced by the time
        return READY, "%s gets a new name every run (%s = date and time)." % (
            name.replace(_resolved_time_stamp(name), TIME_STAMP), TIME_STAMP)
    if os.path.isdir(out_path):
        return READY, "%s is writable." % out_path
    return WARN, ("%s is overwritten every run. Add %s to the name to keep every run "
                  "(for example Report_%s.csv)." % (name, TIME_STAMP, TIME_STAMP))


def check_input_dataset(value):
    """(status, note) for one input. A scheduled run reads the saved project, not what is
    open in ArcGIS Pro: Esri recommends full paths to datasets instead of map layers."""
    text = str(value)
    try:
        d = arcpy.Describe(value)
        dtype = getattr(d, "dataType", "")
    except Exception:
        return FAIL, "%s cannot be read." % text
    if dtype in ("FeatureLayer", "RasterLayer", "Layer", "TableView", "MosaicLayer"):
        src = getattr(d, "catalogPath", "") or ""
        return FAIL, "%s is a map layer. Use the full path instead: %s" % (text, src)
    if not os.path.isabs(text) and "://" not in text:
        return FAIL, "%s is not a full path." % text
    return READY, "%s is a dataset path (%s)." % (os.path.basename(text.rstrip("\\/")) or text, dtype)


def check_schedule_readiness(outputs=None, inputs=None, check_signin=True, out_report=None):
    """Core logic of Check Schedule Readiness. Returns dict(ready, rows, counts, seconds)."""
    t0 = time.time()
    rows = []

    def add(check, status, note):
        rows.append(dict(check=check, status=status, note=note))
        {READY: arcpy.AddMessage, WARN: arcpy.AddWarning, FAIL: arcpy.AddWarning}[status](
            "%s  %s: %s" % (status, check, note))

    info = arcpy.GetInstallInfo()
    lic = info.get("LicenseType", "")
    add("ArcGIS Pro", READY, "ArcGIS Pro %s, %s license." % (info.get("Version", ""), lic or "unknown"))
    if check_signin:
        arcpy.SetProgressorLabel("Signing in from a new Python process...")
        status, note, _ = test_signin_outside_pro()
        add("Sign in outside ArcGIS Pro", status, note)
    elif "named" in lic.lower():
        add("Sign in outside ArcGIS Pro", WARN, "Not tested. Named User license: Sign in automatically is required.")
    for o in outputs or []:
        status, note = check_output_location(str(o))
        add("Output", status, note)
    for i in inputs or []:
        status, note = check_input_dataset(i)
        add("Input", status, note)
    add("Before you schedule", WARN if not (inputs or outputs) else READY,
        "Save the project, and stay signed in to Windows: scheduled tools run only while you are signed in.")
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in (READY, WARN, FAIL)}
    ready = counts[FAIL] == 0
    if out_report:
        with open(out_report, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["check", "status", "note"])
            w.writeheader()
            w.writerows(rows)
    secs = round(time.time() - t0, 1)
    arcpy.AddMessage("%s: %d pass, %d warning(s), %d fail, %.1f s." % (
        "Ready to schedule" if ready else "Not ready to schedule", counts[READY], counts[WARN], counts[FAIL], secs))
    return dict(ready=ready, rows=rows, counts=counts, seconds=secs)


class CheckScheduleReadiness:
    """Checks what a scheduled run needs before you use Run > Schedule: a sign-in
    that works outside ArcGIS Pro, full paths for inputs, writable outputs, and a
    time stamp in output names. Changes nothing. Episode A8 builds this tool."""

    def __init__(self):
        self.label = "Check Schedule Readiness"
        self.description = ("Checks a tool's inputs and outputs before you schedule it: signs in to your "
                            "portal from a new Python process (the way a scheduled run does), checks that "
                            "inputs are full dataset paths and not map layers, that output folders are "
                            "writable, and whether output names carry the %t% time stamp. Changes nothing.")
        self.category = "Scheduling"

    def getParameterInfo(self):
        outputs = arcpy.Parameter(displayName="Outputs of the Tool to Schedule", name="outputs", datatype=["DEFile", "DEFolder"],
                                  parameterType="Optional", direction="Input", multiValue=True)
        inputs = arcpy.Parameter(displayName="Inputs of the Tool to Schedule", name="inputs",
                                 datatype=["GPFeatureLayer", "GPTableView", "DEWorkspace"],
                                 parameterType="Optional", direction="Input", multiValue=True)
        signin = arcpy.Parameter(displayName="Test Portal Sign-In Outside ArcGIS Pro", name="check_signin",
                                 datatype="GPBoolean", parameterType="Optional", direction="Input")
        signin.value = True
        report = arcpy.Parameter(displayName="Output Checklist", name="out_report", datatype="DEFile",
                                 parameterType="Optional", direction="Output")
        report.filter.list = ["csv"]
        ready = arcpy.Parameter(displayName="Ready", name="ready", datatype="GPBoolean",
                                parameterType="Derived", direction="Output")
        return [outputs, inputs, signin, report, ready]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        # An output typed in a tool dialog may not exist yet: the check reads its folder, so
        # the Outputs parameter must not fail validation for a file that is not there.
        if parameters[0].hasError():
            parameters[0].clearMessage()
        for v in (parameters[0].values or []):
            if TIME_STAMP not in str(v) and not _resolved_time_stamp(os.path.basename(str(v))) and not os.path.isdir(str(v)):
                parameters[0].setWarningMessage("An output without %s is overwritten every run." % TIME_STAMP)
                break
        return

    def execute(self, parameters, messages):
        outs = [str(v) for v in (parameters[0].values or [])]
        ins = [v for v in (parameters[1].values or [])]
        result = check_schedule_readiness(outs, ins, bool(parameters[2].value), parameters[3].valueAsText)
        parameters[4].value = result["ready"]
        return

    def postExecute(self, parameters):
        return


# ---------------------------------------------------------------------------
# Copy-Me Template: copy this class to start a new tool
# ---------------------------------------------------------------------------
class CopyMeTemplate:
    """Starting point for a new tool. Copy the whole class, rename it (letters
    and numbers only), change the label, keep the parameters you need, put your
    logic in execute, and add the new class name to Toolbox.tools."""

    def __init__(self):
        self.label = "Copy-Me Template"
        self.description = "A starting point for a new tool. It lists its inputs and changes nothing."
        self.category = "Templates"

    def getParameterInfo(self):
        # One of each common parameter type; delete the ones you do not need.
        in_features = arcpy.Parameter(displayName="Input Features", name="in_features",
                                      datatype="GPFeatureLayer", parameterType="Required",
                                      direction="Input")
        field = arcpy.Parameter(displayName="Field", name="field", datatype="Field",
                                parameterType="Optional", direction="Input")
        field.parameterDependencies = [in_features.name]          # fields of the input
        folder = arcpy.Parameter(displayName="Folder", name="folder", datatype="DEFolder",
                                 parameterType="Optional", direction="Input")
        choice = arcpy.Parameter(displayName="Choice", name="choice", datatype="GPString",
                                 parameterType="Optional", direction="Input")
        choice.filter.type = "ValueList"                           # a drop-down list
        choice.filter.list = ["Option A", "Option B"]
        choice.value = "Option A"
        number = arcpy.Parameter(displayName="Number", name="number", datatype="GPDouble",
                                 parameterType="Optional", direction="Input")
        number.filter.type = "Range"                               # a min / max check
        number.filter.list = [0, 100]
        flag = arcpy.Parameter(displayName="Flag", name="flag", datatype="GPBoolean",
                               parameterType="Optional", direction="Input")
        flag.value = False                                         # a check box
        return [in_features, field, folder, choice, number, flag]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        # Read each parameter by its position in getParameterInfo:
        #   .valueAsText for paths and expressions, .value for numbers and check boxes.
        for p in parameters:
            arcpy.AddMessage("%s = %s" % (p.displayName, p.valueAsText))
        return

    def postExecute(self, parameters):
        return
