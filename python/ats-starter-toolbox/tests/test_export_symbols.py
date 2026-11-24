# Headless test for "Export Pro Symbols to SVG/PNG" (episode A6, smart tool dialogs). Self-contained: builds a
# small synthetic style (.stylx = SQLite, ITEMS table) in tests\_scratch\export_symbols\ (re-created on every run),
# drives the dialog methods (updateParameters / updateMessages) the way the Pro dialog does, then runs the tool
# through arcpy.ImportToolbox. Run with the ArcGIS Pro Python:  propy.bat tests\test_export_symbols.py
# Exit code 0 = PASS.
import os, sys, shutil, json, hashlib, sqlite3, importlib.machinery, importlib.util
import xml.etree.ElementTree as ET
import arcpy
sys.dont_write_bytecode = True   # loading the .pyt as a module below must not leave __pycache__ in the toolbox folder

HERE = os.path.dirname(os.path.abspath(__file__))
PYT = os.path.join(os.path.dirname(HERE), "ATS-Starter.pyt")
S = os.path.join(HERE, "_scratch", "export_symbols")
fails = []
facts = {}


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg, flush=True)
    if not cond: fails.append(msg)


def rgb(r, g, b, a=100):
    return {"type": "CIMRGBColor", "values": [r, g, b, a]}


def poly_sym(fill=None, stroke=None, width=1.0):
    layers = []
    if stroke: layers.append({"type": "CIMSolidStroke", "enable": True, "width": width, "color": stroke})
    if fill: layers.append({"type": "CIMSolidFill", "enable": True, "color": fill})
    return {"type": "CIMPolygonSymbol", "symbolLayers": layers}


def marker(geometry, symbol, size=20, frame=(0, 0, 10, 10)):
    return {"type": "CIMPointSymbol", "symbolLayers": [{
        "type": "CIMVectorMarker", "enable": True, "size": size, "anchorPointUnits": "Relative",
        "anchorPoint": {"x": 0, "y": 0}, "scaleSymbolsProportionally": True, "respectFrame": True,
        "frame": dict(zip(("xmin", "ymin", "xmax", "ymax"), frame)),
        "markerGraphics": [{"type": "CIMMarkerGraphic", "geometry": geometry, "symbol": symbol}]}]}


RED, BLUE, BLACK = rgb(220, 30, 30), rgb(30, 60, 220), rgb(0, 0, 0)
ITEMS = [  # (class, category, name, cim)
    (3, "Basic", "Square", marker({"rings": [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]]}, poly_sym(RED, BLACK, 0.5))),
    (3, "Basic", "Dot", marker({"curveRings": [[[5, 10], {"a": [[5, 10], [5, 5], 0, 1]}]]}, poly_sym(BLUE))),
    (3, "Basic", "Lens", marker({"curveRings": [[[0, 5], {"c": [[10, 5], [5, 8]]}, {"c": [[0, 5], [5, 2]]}]]}, poly_sym(RED))),
    (3, "Basic", "Drop", marker({"curveRings": [[[5, 10], {"b": [[5, 0], [11, 4], [8, 0]]}, {"b": [[5, 10], [2, 0], [-1, 4]]}]]}, poly_sym(BLUE))),
    (3, "Extra", "Dot", marker({"curveRings": [[[5, 10], {"a": [[5, 10], [5, 5], 0, 0]}]]}, poly_sym(RED))),
    (3, "Extra", "Tick", marker({"paths": [[[1, 5], [4, 2], [9, 9]]]},
                                {"type": "CIMLineSymbol", "symbolLayers": [{"type": "CIMSolidStroke", "enable": True, "width": 1.5, "color": BLACK}]})),
    (3, None, "Loose", marker({"rings": [[[0, 0], [5, 10], [10, 0], [0, 0]]]}, poly_sym(BLACK))),
    (4, "Basic", "A line symbol", {"type": "CIMLineSymbol", "symbolLayers": []}),   # not a point symbol: ignored
]


def make_style(path, items):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE ITEMS (ID INTEGER PRIMARY KEY, CLASS INTEGER, CATEGORY TEXT, NAME TEXT, TAGS TEXT, CONTENT TEXT, KEY TEXT UNIQUE)")
    con.execute("CREATE TABLE meta (key TEXT, value TEXT)")
    con.executemany("INSERT INTO meta VALUES (?, ?)", [("version", "1.0"), ("content", "json")])
    con.executemany("INSERT INTO ITEMS (CLASS, CATEGORY, NAME, TAGS, CONTENT, KEY) VALUES (?,?,?,?,?,?)",
                    [(c, cat, n, "", json.dumps(cim), "%s_%s_%d" % (n, cat, c)) for c, cat, n, cim in items])
    con.commit(); con.close()


def outputs(result):
    """Every file under the derived output folder (the tool returns the folder it wrote to)."""
    folder = result.getOutput(0)
    return sorted(os.path.join(r, f) for r, d, fs in os.walk(folder) for f in fs)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


if os.path.exists(S): shutil.rmtree(S)
os.makedirs(S)
style = os.path.join(S, "Test Icons.stylx")          # a space in the name on purpose
make_style(style, ITEMS)
empty_style = os.path.join(S, "Lines only.stylx")
make_style(empty_style, [ITEMS[-1]])
not_style = os.path.join(S, "Not a style.stylx")
open(not_style, "w").write("this is not a database")
style_hash = sha(style)

# ---- the module, the way Pro loads it -----------------------------------------------------------
loader = importlib.machinery.SourceFileLoader("ats_starter_mod", PYT)
spec = importlib.util.spec_from_loader("ats_starter_mod", loader)
mod = importlib.util.module_from_spec(spec); loader.exec_module(mod)
tool = mod.ExportProSymbols()
check(tool.category == "Symbology" and tool.label == "Export Pro Symbols to SVG/PNG", "label + category Symbology")
cat = mod.read_style_catalog(style)
check(len(cat) == 7, "catalog: 7 point symbols, the line symbol ignored (%d)" % len(cat))
check(sorted({c for c, n in cat}, key=str.lower) == ["(no category)", "Basic", "Extra"], "catalog: categories incl. (no category)")

# ---- the dialog: updateParameters / updateMessages ----------------------------------------------
P = tool.getParameterInfo()
names = [p.name for p in P]
check(names == ["in_style", "scope", "categories", "symbols", "out_folder", "out_format", "png_size", "out_location"], "parameter order %s" % names)
check(P[0].filter.type == "File" and list(P[0].filter.list) == ["stylx"], "Input Style: File filter stylx (%s %s)" % (P[0].filter.type, P[0].filter.list))
check(P[6].filter.type == "Range" and list(P[6].filter.list) == [16, 1024] and P[6].value == 256, "PNG Size: Range 16-1024, default 256")
check(P[2].parameterType == "Optional" and P[3].parameterType == "Optional" and P[2].multiValue and P[3].multiValue,
      "Categories + Symbols are optional multivalue")


def validate(params):
    for p in params: p.clearMessage()
    tool.updateParameters(params)
    tool.updateMessages(params)


P[0].value = style
P[4].value = S
validate(P)
check(list(P[2].filter.list) == ["(no category)", "Basic", "Extra"], "Categories list filled from the style: %s" % list(P[2].filter.list))
check(len(P[3].filter.list) == 7 and "Dot (Basic)" in P[3].filter.list and "Dot (Extra)" in P[3].filter.list,
      "Symbols list filled: 7 labels, repeated names told apart")
check(P[2].enabled is False and P[3].enabled is False, "Export = All: Categories and Symbols switched off")
check(not any(p.hasError() for p in P), "Export = All: no errors")
check(P[4].hasWarning() and "not empty" in (P[4].message or ""), "non-empty output folder: warning only")
facts["folder_warning"] = P[4].message

P[1].value = "Selected categories"
validate(P)
check(P[2].enabled and not P[3].enabled, "Export = Selected categories: Categories on, Symbols off")
check(P[2].hasError(), "Selected categories + no category = error on Categories (optional acts as required)")
facts["msg_735"] = P[2].message
check("735" in (P[2].message or "") or "required" in (P[2].message or "").lower(), "error text is the system message 735: %r" % P[2].message)

P[2].values = ["Extra"]
validate(P)
check(not P[2].hasError(), "a category picked: error cleared")
check(list(P[3].filter.list) == ["Dot (Extra)", "Tick (Extra)"], "Symbols list depends on Categories: %s" % list(P[3].filter.list))

P[1].value = "Selected symbols"
validate(P)
check(P[3].enabled and P[3].hasError(), "Export = Selected symbols + none picked = error on Symbols")
P[3].values = ["Tick (Extra)"]
validate(P)
check(not P[3].hasError(), "a symbol picked: error cleared")

P[5].value = "SVG"
validate(P)
check(P[6].enabled is False, "Output Format = SVG: PNG Size switched off")
P[5].value = "SVG and PNG"
validate(P)
check(P[6].enabled is True, "Output Format = SVG and PNG: PNG Size on")

# a different style: picks that are not in the new style are dropped
P[0].value = empty_style
validate(P)
check(P[0].hasError() and "no point symbols" in P[0].message, "style without point symbols: error on Input Style")
P[0].value = not_style
validate(P)
check(P[0].hasError() and "not an ArcGIS Pro style" in P[0].message, "a file that is not a style: error on Input Style")

Q = tool.getParameterInfo()
Q[0].value = style; Q[1].value = "Selected categories"; Q[2].values = ["Basic", "Extra"]
validate(Q)
Q[2].values = ["Basic"]
Q[3].values = ["Tick (Extra)"]
validate(Q)
check(list(Q[3].filter.list) == ["Dot (Basic)", "Drop (Basic)", "Lens (Basic)", "Square (Basic)"], "Symbols list narrows when Categories change")
check(not Q[3].values, "a picked symbol outside the new category list is dropped (%s)" % Q[3].values)

# ---- the tool, run the way Pro runs it -----------------------------------------------------------
arcpy.ImportToolbox(PYT)
for t in ("BatchClipByFeatureClass", "ExportFeaturesToFolder", "CopyMeTemplate", "ExportProSymbols"):
    check(hasattr(arcpy, t + "_atsstarter"), "toolbox exposes %s_atsstarter" % t)

out = os.path.join(S, "out_all"); os.makedirs(out)
r = arcpy.ExportProSymbols_atsstarter(style, "All point symbols", None, None, out, "SVG and PNG", 128)
files = outputs(r)
check(len(files) == 14, "All: 7 symbols x SVG + PNG = 14 files (%d)" % len(files))
check("Exported 7 symbol(s), 14 file(s), 0 skipped" in r.getMessages(), "All: summary message")
check(sorted(os.listdir(out)) == ["(no category)", "Basic", "Extra"], "one subfolder per category")
from PIL import Image
for f in files:
    if f.endswith(".svg"):
        root = ET.parse(f).getroot()
        ok = root.tag.endswith("svg") and root.get("width") == "128" and len(list(root)) >= 1
        check(ok, "SVG well-formed, 128 px, has shapes: %s" % os.path.relpath(f, out))
    else:
        im = Image.open(f)
        bbox = im.getchannel("A").getbbox()
        check(im.size == (128, 128) and im.mode == "RGBA" and bbox is not None, "PNG 128 x 128 RGBA, not empty: %s" % os.path.relpath(f, out))
sq = Image.open(os.path.join(out, "Basic", "Square.png")).convert("RGBA").getpixel((64, 64))
check(sq[0] > 200 and sq[1] < 60 and sq[3] == 255, "Square.png centre is red %s" % (sq,))
dot = Image.open(os.path.join(out, "Basic", "Dot.png")).convert("RGBA")
bb = dot.getchannel("A").getbbox()
w, h = bb[2] - bb[0], bb[3] - bb[1]
check(abs(w - h) <= 2 and w >= 118 and dot.getpixel((64, 64))[2] > 200 and dot.getpixel((2, 2))[3] == 0,
      "Dot.png: full circle from an 'a' arc fills the square (%dx%d), corners transparent" % (w, h))
facts["dot_bbox"] = bb

check(not [f for f in files if not f.endswith((".svg", ".png"))], "only .svg and .png files (no metadata sidecars)")
out2 = os.path.join(S, "out_one"); os.makedirs(out2)
r = arcpy.ExportProSymbols_atsstarter(style, "Selected symbols", None, ["Dot (Extra)"], out2, "SVG", 64)
check([os.path.relpath(f, out2) for f in outputs(r)] == [os.path.join("Extra", "Dot.svg")], "Selected symbols: only Extra\\Dot.svg")

out3 = os.path.join(S, "out_cat"); os.makedirs(out3)
r = arcpy.ExportProSymbols_atsstarter(style, "Selected categories", ["Basic"], None, out3, "PNG", 64)
check(len(outputs(r)) == 4 and all(f.endswith(".png") for f in outputs(r)), "Selected categories Basic: 4 PNG")

# validation also runs for a scripted call: the optional-as-required rule and the Range filter stop the tool
for label, args in [("no category picked", (style, "Selected categories", None, None, out2, "SVG", 64)),
                    ("PNG Size 5 outside 16-1024", (style, "All point symbols", None, None, out2, "PNG", 5)),
                    ("not a style", (not_style, "All point symbols", None, None, out2, "SVG", 64))]:
    try:
        arcpy.ExportProSymbols_atsstarter(*args)
        check(False, "scripted call fails: " + label)
    except arcpy.ExecuteError:
        msg = arcpy.GetMessages(2)
        facts["scripted_" + label] = msg
        check(True, "scripted call fails: %s -> %s" % (label, msg.replace("\n", " | ")[:160]))

check(sha(style) == style_hash, "the style file is unchanged (read only)")
json.dump(facts, open(os.path.join(S, "facts.json"), "w"), indent=1, default=str)
print("RESULT", "FAIL %d" % len(fails) if fails else "PASS")
sys.exit(1 if fails else 0)
