# -*- coding: utf-8 -*-
"""Symbol Tools: episode A6 of the All Things Spatial "Automate ArcGIS Pro" series.
One tool, Export Pro Symbols to SVG/PNG, with a smart dialog. The same tool is in the ATS Starter Toolbox."""
import json
import math
import os
import re
import sqlite3
import time

import arcpy


class Toolbox:
    def __init__(self):
        self.label = "Symbol Tools"
        self.alias = "symboltools"
        self.tools = [ExportProSymbols]


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
