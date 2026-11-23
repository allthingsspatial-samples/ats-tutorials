# -*- coding: utf-8 -*-
"""
Export Pro Symbols to SVG/PNG -- standalone ArcGIS Pro Python toolbox.

Extract ArcGIS Pro point symbols from a .stylx file to clean, scalable SVG
(and, optionally, rasterized PNG at a fixed pixel size). Export everything in a
style, selected categories, or a single symbol -- ideal for CDN/popup hero icons,
web legends, and design handoff. A .stylx is just a SQLite database whose ITEMS
table holds each symbol's CIM JSON; this tool reads that JSON and composes an SVG
directly, with NO arcpy dependency in the rendering core (so it is testable
anywhere). PNG is produced by rasterizing the SVG with cairosvg or Inkscape.

MAKE IT YOURS: point STYLX at any .stylx (blank auto-detects your Pro Favorites),
choose a scope, set the target pixel size, and run. Everything below is plain
Python -- only the Toolbox/Tool wrapper touches arcpy.

Runtime: arcgispro-py3 (ArcGIS Pro 3.x). The SVG core needs only the standard
library (sqlite3 + json). PNG output needs cairosvg (`pip install cairosvg
--break-system-packages`) OR a local Inkscape install; without either, SVGs are
still written and PNGs are skipped with a note. Adapted from an All Things Spatial
workflow.

-----------------------------------------------------------------------------
MIT License

Copyright (c) 2026 All Things Spatial LLC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
-----------------------------------------------------------------------------
"""
import base64
import json
import math
import os
import re
import shutil
import subprocess
import sqlite3
from pathlib import Path

import arcpy


# ============================================================================
# CONFIG -- only used when you run this file directly (python this.pyt) for a
# quick command-line test. The Pro tool dialog overrides all of these.
# ============================================================================
STYLX_PATH = r"C:\path\to\Favorites.stylx"   # blank/None in the tool = auto-detect Favorites
SCOPE      = "all"                            # "all" | "categories" | "single"
CATEGORIES = []                               # used when SCOPE = "categories"
SYMBOL     = None                             # used when SCOPE = "single"
SVG_DIR    = r"C:\path\to\out\svg"            # where .svg files are written
PNG_DIR    = None                             # None = same folder as SVG
WRITE_PNG  = True                             # also rasterize a PNG per symbol
TARGET_PX  = 200                              # output width = height, in pixels


_DATA_URL = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$", re.DOTALL)
_RASTER_EXT = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg",
    "image/gif": ".gif", "image/bmp": ".bmp",
}


def _noop(*_a, **_k):
    pass


# ---------------------------------------------------------------------------
# .stylx discovery + enumeration  (a .stylx is a SQLite DB with an ITEMS table:
# NAME, CATEGORY, CLASS, CONTENT -- where CONTENT is the symbol's CIM JSON)
# ---------------------------------------------------------------------------
def find_favorites_stylx():
    """Probe ArcGIS Pro's standard locations for Favorites.stylx; return Path or None."""
    appdata = Path(os.environ.get("APPDATA", ""))
    localappdata = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        appdata / "ESRI" / "ArcGISPro" / "ArcGIS" / "Favorites.stylx",
        appdata / "ESRI" / "ArcGISPro" / "Favorites.stylx",
        localappdata / "ESRI" / "ArcGISPro" / "ArcGIS" / "Favorites.stylx",
        localappdata / "ESRI" / "ArcGISPro" / "Favorites.stylx",
    ]
    for p in candidates:
        if p.exists():
            return p
    for root in (appdata, localappdata):
        if root and root.exists():
            for hit in root.rglob("Favorites.stylx"):
                return hit
    return None


def list_categories(stylx_path):
    """Distinct, sorted category names in the style ('' -> '(uncategorized)')."""
    con = sqlite3.connect(str(stylx_path))
    try:
        rows = con.execute("SELECT DISTINCT CATEGORY FROM ITEMS").fetchall()
    finally:
        con.close()
    cats = sorted({(r[0] or "(uncategorized)") for r in rows}, key=str.lower)
    return cats


def list_names(stylx_path, categories=None):
    """Sorted symbol names, optionally filtered to the given categories."""
    con = sqlite3.connect(str(stylx_path))
    try:
        if categories:
            wanted = set(categories)
            rows = con.execute("SELECT NAME, CATEGORY FROM ITEMS").fetchall()
            names = [n for (n, c) in rows if (c or "(uncategorized)") in wanted]
        else:
            names = [r[0] for r in con.execute("SELECT NAME FROM ITEMS").fetchall()]
    finally:
        con.close()
    return sorted({n for n in names if n}, key=str.lower)


def fetch_symbol(stylx_path, name):
    """Read the named symbol's CIM JSON dict from a .stylx (SQLite) file."""
    con = sqlite3.connect(str(stylx_path))
    try:
        rows = con.execute(
            "SELECT NAME, CATEGORY, CLASS, CONTENT FROM ITEMS "
            "WHERE NAME = ? COLLATE NOCASE", (name,),
        ).fetchall()
    finally:
        con.close()
    if not rows:
        raise LookupError("No style item named {!r}".format(name))
    raw = rows[0][3]
    if isinstance(raw, bytes):
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        raw = raw.decode("utf-8", errors="replace")
    elif raw.startswith("﻿"):
        raw = raw[1:]
    obj, _end = json.JSONDecoder().raw_decode(raw.lstrip())
    return obj


def safe_filename(name):
    """Filesystem-safe base name from a symbol name."""
    keep = [c if (c.isalnum() or c in (" ", "-", "_")) else "_" for c in (name or "symbol")]
    return "_".join("".join(keep).split()) or "symbol"


# ---------------------------------------------------------------------------
# CIM -> SVG composition
# ---------------------------------------------------------------------------
def all_marker_layers(symbol_cim):
    sym = symbol_cim.get("symbol", symbol_cim)
    out = [l for l in sym.get("symbolLayers", []) if "Marker" in l.get("type", "")]
    if not out:
        raise ValueError("No marker layers found in symbol")
    return out


def _safe_size(layer, fallback=64.0):
    try:
        s = float(layer.get("size"))
    except (TypeError, ValueError):
        s = 0.0
    return s if s > 0 else fallback


def _split_color(values):
    if not values or len(values) < 3:
        return ("rgb(0,0,0)", 1.0)
    r, g, b = int(values[0]), int(values[1]), int(values[2])
    a = (values[3] / 100.0) if len(values) >= 4 else 1.0
    return ("rgb({},{},{})".format(r, g, b), a)


def _extract_paint(symbol):
    paint = {"fill": "none", "fill_opacity": 1.0, "stroke": "none",
             "stroke_opacity": 1.0, "stroke_width": 0.0}
    for sl in (symbol or {}).get("symbolLayers", []):
        if not sl.get("enable", True):
            continue
        t = sl.get("type", "")
        rgb, op = _split_color((sl.get("color") or {}).get("values", [0, 0, 0, 100]))
        if "Solid" in t and "Fill" in t:
            paint["fill"], paint["fill_opacity"] = rgb, op
        elif "Solid" in t and "Stroke" in t:
            paint["stroke"], paint["stroke_opacity"] = rgb, op
            paint["stroke_width"] = float(sl.get("width", 0))
    return paint


def _arc_to_svg(start, seg):
    end, center = seg[0], seg[1]
    cw = bool(seg[3]) if len(seg) > 3 else False
    sx, sy = start; ex, ey = end; cx, cy = center
    rx = math.hypot(sx - cx, sy - cy)
    sweep = 0 if cw else 1
    EPS = 1e-9
    if abs(sx - ex) < EPS and abs(sy - ey) < EPS:
        mx, my = 2 * cx - sx, 2 * cy - sy
        cmd = ("A{0} {0} 0 0 {1} {2} {3} A{0} {0} 0 0 {1} {4} {5}"
               .format(rx, sweep, mx, my, ex, ey))
        return cmd, end
    a0 = math.atan2(sy - cy, sx - cx)
    a1 = math.atan2(ey - cy, ex - cx)
    da = a1 - a0
    while da > math.pi: da -= 2 * math.pi
    while da <= -math.pi: da += 2 * math.pi
    large = 1 if abs(da) > math.pi else 0
    return "A{0} {0} 0 {1} {2} {3} {4}".format(rx, large, sweep, ex, ey), end


def _segments_to_d(rings_or_paths, closed):
    parts, skipped = [], 0
    for ring in rings_or_paths:
        if not ring:
            continue
        first = ring[0]
        if isinstance(first, dict):
            skipped += 1
            continue
        cx, cy = first
        parts.append("M{} {}".format(cx, cy))
        for seg in ring[1:]:
            if isinstance(seg, list) and len(seg) == 2 and not isinstance(seg[0], (list, dict)):
                cx, cy = seg
                parts.append("L{} {}".format(cx, cy))
            elif isinstance(seg, dict):
                if "c" in seg or "b" in seg:
                    pts = seg.get("c", seg.get("b"))
                    end = pts[0]
                    if len(pts) >= 3:
                        c1, c2 = pts[1], pts[2]
                        parts.append("C{} {} {} {} {} {}".format(
                            c1[0], c1[1], c2[0], c2[1], end[0], end[1]))
                    elif len(pts) == 2:
                        ctrl = pts[1]
                        parts.append("Q{} {} {} {}".format(ctrl[0], ctrl[1], end[0], end[1]))
                    else:
                        skipped += 1
                        continue
                    cx, cy = end
                elif "q" in seg:
                    end, ctrl = seg["q"]
                    parts.append("Q{} {} {} {}".format(ctrl[0], ctrl[1], end[0], end[1]))
                    cx, cy = end
                elif "a" in seg:
                    cmd, end = _arc_to_svg((cx, cy), seg["a"])
                    parts.append(cmd); cx, cy = end
                else:
                    skipped += 1
            else:
                skipped += 1
        if closed:
            parts.append("Z")
    return " ".join(parts), skipped


def _path_attrs(paint, override_fill=None):
    fill = override_fill if override_fill is not None else paint["fill"]
    parts = ['fill="{}"'.format(fill)]
    if fill != "none":
        parts.append('fill-opacity="{:.4f}"'.format(paint["fill_opacity"]))
        parts.append('fill-rule="evenodd"')
    parts.append('stroke="{}"'.format(paint["stroke"]))
    if paint["stroke"] != "none":
        parts.append('stroke-opacity="{:.4f}"'.format(paint["stroke_opacity"]))
    parts.append('stroke-width="{}"'.format(paint["stroke_width"]))
    return " ".join(parts)


def build_vector_layer_body(layer):
    out, processed, skipped = [], 0, 0
    for g in layer.get("markerGraphics", []):
        geom = g.get("geometry", {})
        paint = _extract_paint(g.get("symbol", {}))
        d, closed = None, True
        if "rings" in geom:
            d, sk = _segments_to_d(geom["rings"], True)
        elif "curveRings" in geom:
            d, sk = _segments_to_d(geom["curveRings"], True)
        elif "paths" in geom:
            d, sk = _segments_to_d(geom["paths"], False); closed = False
        elif "curvePaths" in geom:
            d, sk = _segments_to_d(geom["curvePaths"], False); closed = False
        elif "x" in geom and "y" in geom:
            r = float(g.get("size", 1))
            out.append('<circle cx="{}" cy="{}" r="{}" {}/>'.format(
                geom["x"], geom["y"], r, _path_attrs(paint)))
            processed += 1
            continue
        else:
            skipped += 1
            continue
        if d:
            override = None if closed else "none"
            out.append('<path d="{}" {}/>'.format(d, _path_attrs(paint, override_fill=override)))
            processed += 1
            skipped += sk
    return "\n      ".join(out), processed, skipped


def build_picture_layer_body(layer, raster_base):
    m = _DATA_URL.match(layer.get("url", ""))
    if not m:
        raise ValueError("CIMPictureMarker.url is not a base64 data URL")
    mime = m.group("mime").lower()
    raw = base64.b64decode(m.group("data"))
    ext = ".svg" if "svg" in mime else _RASTER_EXT.get(mime, ".bin")
    raster_path = Path(str(raster_base) + ext)
    raster_path.write_bytes(raw)
    size = _safe_size(layer)
    href = raster_path.name
    return ('<image href="{0}" xlink:href="{0}" x="0" y="0" width="{1}" height="{1}"/>'
            .format(href, size)), 1, 0


def _layer_transform(layer, viewbox_size):
    size = _safe_size(layer)
    frame = layer.get("frame", {"xmin": 0, "ymin": 0, "xmax": size, "ymax": size})
    fx, fy = float(frame["xmin"]), float(frame["ymin"])
    fw = float(frame["xmax"]) - fx
    fh = float(frame["ymax"]) - fy
    fmax = max(fw, fh) if max(fw, fh) > 0 else 1.0
    scale = size / fmax
    pad = (viewbox_size - size) / 2.0
    tx = pad - scale * fx
    ty = pad + scale * (fy + fh)
    return "translate({} {}) scale({} {})".format(tx, ty, scale, -scale), scale


def build_symbol_svg(symbol_cim, target_size_px, raster_base=None, say=_noop):
    """Compose every marker layer into one SVG string. `raster_base` is a path
    stem for any picture-marker sidecar files (defaults to cwd 'layer')."""
    layers = all_marker_layers(symbol_cim)
    sizes = [_safe_size(l) for l in layers]
    viewbox = max(sizes) if sizes else 64.0

    max_half_stroke_vb = 0.0
    for layer in layers:
        layer_size = _safe_size(layer)
        frame = layer.get("frame", {"xmin": 0, "ymin": 0, "xmax": layer_size, "ymax": layer_size})
        fw = float(frame["xmax"]) - float(frame["xmin"])
        fh = float(frame["ymax"]) - float(frame["ymin"])
        fmax = max(fw, fh) if max(fw, fh) > 0 else 1.0
        layer_scale = layer_size / fmax
        for g in layer.get("markerGraphics", []):
            half = (_extract_paint(g.get("symbol", {}))["stroke_width"] * layer_scale) / 2.0
            max_half_stroke_vb = max(max_half_stroke_vb, half)

    pad = max_half_stroke_vb + viewbox * 0.01
    vb_origin = -pad
    vb_size = viewbox + 2 * pad

    groups = []
    for i, layer in enumerate(reversed(layers)):
        cim_index = len(layers) - 1 - i
        kind = layer.get("type")
        transform, _scale = _layer_transform(layer, viewbox)
        try:
            if kind == "CIMVectorMarker":
                body, p, sk = build_vector_layer_body(layer)
            elif kind == "CIMPictureMarker":
                base = "{}_layer{}".format(raster_base or "layer", cim_index)
                body, p, sk = build_picture_layer_body(layer, base)
            else:
                say("  skip layer {}: {} (not handled)".format(cim_index, kind))
                continue
        except Exception as e:  # noqa: BLE001
            say("  layer {} ({}) failed: {}".format(cim_index, kind, e))
            continue
        say("  layer {}: {} -> {} graphics, {} skipped".format(cim_index, kind, p, sk))
        groups.append('  <g id="layer{}" transform="{}">\n      {}\n  </g>'
                      .format(cim_index, transform, body))

    return ('<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            'viewBox="{0} {0} {1} {1}" width="{2}" height="{2}">\n{3}\n</svg>\n'
            .format(vb_origin, vb_size, target_size_px, "\n".join(groups)))


# ---------------------------------------------------------------------------
# PNG rasterization (cairosvg -> Inkscape -> skip)
# ---------------------------------------------------------------------------
def _find_inkscape():
    on_path = shutil.which("inkscape")
    if on_path:
        return on_path
    for c in (r"C:\Program Files\Inkscape\bin\inkscape.exe",
              r"C:\Program Files\Inkscape\inkscape.exe"):
        if Path(c).exists():
            return c
    return None


def export_png_from_svg(svg_content, png_path, target_size, say=_noop):
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_content.encode("utf-8"),
                         output_width=target_size, output_height=target_size,
                         write_to=str(png_path))
        return png_path
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001
        say("cairosvg failed: {}".format(e))
    ink = _find_inkscape()
    if ink:
        tmp = Path(str(png_path) + ".tmp.svg")
        tmp.write_text(svg_content, encoding="utf-8")
        try:
            r = subprocess.run([ink, str(tmp), "--export-filename=" + str(png_path),
                                "--export-width=" + str(target_size),
                                "--export-height=" + str(target_size)],
                               capture_output=True, timeout=60)
            if r.returncode == 0 and png_path.exists():
                return png_path
        except Exception as e:  # noqa: BLE001
            say("Inkscape failed: {}".format(e))
        finally:
            if tmp.exists():
                tmp.unlink()
    say("PNG skipped for {} -- install cairosvg (`pip install cairosvg "
        "--break-system-packages`) or Inkscape.".format(png_path.name))
    return None


# ---------------------------------------------------------------------------
# One symbol -> files, and the batch driver the tool calls
# ---------------------------------------------------------------------------
def export_one(stylx_path, name, svg_dir, png_dir, target_px, write_png, say=_noop):
    """Render one symbol to <svg_dir>/<safe>.svg (+ <png_dir>/<safe>.png).
    Returns (svg_path, png_path_or_None)."""
    svg_dir = Path(svg_dir); svg_dir.mkdir(parents=True, exist_ok=True)
    cim = fetch_symbol(Path(stylx_path), name)
    safe = safe_filename(name)
    svg_path = svg_dir / (safe + ".svg")
    svg = build_symbol_svg(cim, target_px, raster_base=str(svg_dir / safe), say=say)
    svg_path.write_text(svg, encoding="utf-8")
    png_path = None
    if write_png:
        pdir = Path(png_dir) if png_dir else svg_dir
        pdir.mkdir(parents=True, exist_ok=True)
        png_path = export_png_from_svg(svg, pdir / (safe + ".png"), target_px, say=say)
    return svg_path, png_path


def resolve_target_names(stylx_path, scope, categories=None, name=None):
    """Turn the chosen scope into a concrete list of symbol names."""
    if scope == "single":
        return [name] if name else []
    if scope == "categories":
        return list_names(stylx_path, categories=categories)
    return list_names(stylx_path)              # "all"


def export_symbols(stylx_path, scope, svg_dir, png_dir=None, categories=None,
                   name=None, target_px=200, write_png=True, say=_noop):
    """Batch driver. Returns (ok_count, fail_count)."""
    names = resolve_target_names(stylx_path, scope, categories, name)
    say("{} symbol(s) to export.".format(len(names)))
    ok, fail = 0, 0
    for n in names:
        try:
            svg_path, png_path = export_one(stylx_path, n, svg_dir, png_dir,
                                            target_px, write_png, say=say)
            ok += 1
            say("OK  {} -> {}{}".format(
                n, svg_path.name, "" if not png_path else " + " + png_path.name))
        except Exception as e:  # noqa: BLE001
            fail += 1
            say("ERR {} -- {}".format(n, e))
    return ok, fail


def _resolve_stylx(param_text):
    """Return a usable .stylx path string: the param if set, else auto-detected
    Favorites.stylx, else None."""
    if param_text:
        return param_text
    try:
        p = find_favorites_stylx()
        return str(p) if p else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ArcGIS Pro toolbox wrapper (the only part that touches arcpy)
# ---------------------------------------------------------------------------
_SYM_ALL = "All symbols"
_SYM_CATS = "Selected categories"
_SYM_ONE = "Single symbol"

# Cache enumerated categories/names per .stylx path so we don't re-read on every
# validation pass.
_SYMBOL_CACHE = {}


def _stylx_catalog(stylx_path):
    """(categories, names) for a .stylx, cached. Returns ([], []) on failure."""
    if not stylx_path:
        return [], []
    if stylx_path in _SYMBOL_CACHE:
        return _SYMBOL_CACHE[stylx_path]
    try:
        cats = list_categories(stylx_path)
        names = list_names(stylx_path)
        _SYMBOL_CACHE[stylx_path] = (cats, names)
        return cats, names
    except Exception:
        return [], []


class Toolbox:
    def __init__(self):
        self.label = "Export Pro Symbols"
        self.alias = "exportProSymbols"
        self.tools = [ExportProSymbols]


class ExportProSymbols:
    def __init__(self):
        self.label = "Export Pro Symbols to SVG/PNG"
        self.description = (
            "Extract ArcGIS Pro symbols from a .stylx (default: your Favorites) "
            "to SVG and, optionally, PNG at a fixed pixel size. Export everything, "
            "selected categories, or a single symbol -- for CDN/popup hero icons."
        )
        self.canRunInBackground = False
        self.category = "Symbology"

    def getParameterInfo(self):
        # 0 -- style file (.stylx). Blank = auto-detect Favorites.stylx.
        stylx = arcpy.Parameter(
            displayName="Style file (.stylx) -- blank = your Favorites",
            name="stylx", datatype="DEFile",
            parameterType="Optional", direction="Input")
        stylx.filter.list = ["stylx"]

        # 1 -- scope
        scope = arcpy.Parameter(
            displayName="Scope", name="scope",
            datatype="GPString", parameterType="Required", direction="Input")
        scope.filter.type = "ValueList"
        scope.filter.list = [_SYM_ALL, _SYM_CATS, _SYM_ONE]
        scope.value = _SYM_ALL

        # 2 -- categories (when scope = Selected categories)
        categories = arcpy.Parameter(
            displayName="Categories (when scope = Selected categories)",
            name="categories", datatype="GPString",
            parameterType="Optional", direction="Input", multiValue=True)
        categories.filter.type = "ValueList"

        # 3 -- single symbol (when scope = Single symbol)
        symbol = arcpy.Parameter(
            displayName="Symbol (when scope = Single symbol)", name="symbol",
            datatype="GPString", parameterType="Optional", direction="Input")
        symbol.filter.type = "ValueList"

        # 4 -- SVG output folder
        svg_dir = arcpy.Parameter(
            displayName="SVG output folder", name="svg_dir",
            datatype="DEFolder", parameterType="Required", direction="Input")

        # 5 -- PNG output folder (blank = same as SVG folder)
        png_dir = arcpy.Parameter(
            displayName="PNG output folder (blank = same as SVG)", name="png_dir",
            datatype="DEFolder", parameterType="Optional", direction="Input")

        # 6 -- also write PNG
        write_png = arcpy.Parameter(
            displayName="Also write PNG", name="write_png",
            datatype="GPBoolean", parameterType="Optional", direction="Input")
        write_png.value = True

        # 7 -- target size px
        target_px = arcpy.Parameter(
            displayName="Target size (px)", name="target_px",
            datatype="GPLong", parameterType="Optional", direction="Input")
        target_px.value = 200

        # 8 -- derived report
        report = arcpy.Parameter(
            displayName="Result summary", name="report",
            datatype="GPString", parameterType="Derived", direction="Output")

        return [stylx, scope, categories, symbol, svg_dir, png_dir,
                write_png, target_px, report]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        scope = parameters[1].value
        parameters[2].enabled = scope == _SYM_CATS
        parameters[3].enabled = scope == _SYM_ONE

        # Populate categories / names from the resolved .stylx (local SQLite read).
        if parameters[2].enabled and not parameters[2].filter.list:
            cats, _ = _stylx_catalog(_resolve_stylx(parameters[0].valueAsText))
            if cats:
                parameters[2].filter.list = cats
        if parameters[3].enabled and not parameters[3].filter.list:
            _, names = _stylx_catalog(_resolve_stylx(parameters[0].valueAsText))
            if names:
                parameters[3].filter.list = names
        return

    def updateMessages(self, parameters):
        if not _resolve_stylx(parameters[0].valueAsText):
            parameters[0].setWarningMessage(
                "No Favorites.stylx found automatically -- browse to a .stylx file.")
        return

    def execute(self, parameters, messages):
        stylx = _resolve_stylx(parameters[0].valueAsText)
        if not stylx:
            raise arcpy.ExecuteError("No .stylx provided and Favorites.stylx not found.")

        scope_label = parameters[1].value
        scope = ("categories" if scope_label == _SYM_CATS
                 else "single" if scope_label == _SYM_ONE else "all")
        categories = list(parameters[2].values) if parameters[2].values else []
        name = parameters[3].valueAsText
        svg_dir = parameters[4].valueAsText
        png_dir = parameters[5].valueAsText
        write_png = bool(parameters[6].value)
        target_px = int(parameters[7].value or 200)

        messages.addMessage("Style: {}".format(stylx))
        messages.addMessage("Scope: {}{}".format(
            scope_label,
            "" if scope == "all"
            else " -> " + (", ".join(categories) if scope == "categories" else str(name))))

        ok, fail = export_symbols(
            stylx, scope, svg_dir, png_dir=png_dir, categories=categories,
            name=name, target_px=target_px, write_png=write_png,
            say=messages.addMessage)

        summary = "{} exported{}.".format(ok, ", {} failed".format(fail) if fail else "")
        messages.addMessage("\nDone. " + summary)
        parameters[8].value = summary
        return

    def postExecute(self, parameters):
        return


# ---------------------------------------------------------------------------
# Optional command-line smoke test: `python export-pro-symbols-to-svg.pyt`
# Uses the CONFIG block at the top of this file. The Pro tool dialog ignores it.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    _stylx = STYLX_PATH or _resolve_stylx(None)
    if not _stylx or not Path(_stylx).exists():
        print("Set STYLX_PATH in the CONFIG block to a real .stylx file.")
    else:
        ok, fail = export_symbols(
            _stylx, SCOPE, SVG_DIR, png_dir=PNG_DIR, categories=CATEGORIES,
            name=SYMBOL, target_px=TARGET_PX, write_png=WRITE_PNG, say=print)
        print("\nDone. {} exported, {} failed.".format(ok, fail))
