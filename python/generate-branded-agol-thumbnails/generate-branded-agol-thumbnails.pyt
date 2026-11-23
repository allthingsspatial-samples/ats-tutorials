# -*- coding: utf-8 -*-
"""
Generate Branded AGOL Thumbnails -- standalone ArcGIS Pro Python toolbox.

Stamp a consistent branded thumbnail (item TYPE in the header, item TITLE in the
footer) onto every ArcGIS Online item you own -- the whole account or selected
folders -- from one PNG template. Text AUTO-FITS each band by measured pixel width.
Dry-run renders locally without touching the portal.

MAKE IT YOURS: edit HEADER_BOX / FOOTER_BOX to match your own template, the font
auto-fit ranges, or the FONT_CANDIDATES list. Everything is plain Python.

Runtime: arcgispro-py3 (ArcGIS Pro 3.x). Needs Pillow (ships with Pro) + the
ArcGIS API for Python (ships with Pro). Adapted from an All Things Spatial workflow.
"""
import os
from pathlib import Path

import arcpy
from PIL import Image, ImageDraw, ImageFont


# ---- template geometry (px). Edit these to match YOUR template ----------
HEADER_BOX = {"x": 95, "y": 14, "w": 410, "h": 110}   # item TYPE zone  (centered)
FOOTER_BOX = {"x": 24, "y": 296, "w": 338, "h": 98}   # item TITLE zone (left-aligned)

# Font auto-fit ranges (px): Hi = biggest tried; Lo = smallest before ellipsis.
TYPE_SIZE_HI,  TYPE_SIZE_LO  = 54, 30
TITLE_SIZE_HI, TITLE_SIZE_LO = 40, 20
LINE_SPACING = 1.06                  # multiplier on the font's line height
DEFAULT_BRAND_BLUE = "#1C77FF"

# First existing bold TrueType wins (Windows / ArcGIS Notebooks / macOS / Linux).
FONT_CANDIDATES = [
    "arialbd.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "DejaVuSans-Bold.ttf",
]


def resolve_font_path():
    """Return the first usable bold TrueType font path."""
    for cand in FONT_CANDIDATES:
        try:
            ImageFont.truetype(cand, 24)
            return cand
        except OSError:
            continue
    raise OSError("No bold TrueType font found -- add one to FONT_CANDIDATES.")


def _cap_chars(text, max_chars):
    """Pre-cap an absurdly long title at a word boundary <= max_chars, + ellipsis."""
    text = " ".join(text.split())
    if max_chars and len(text) > max_chars:
        clipped = text[:max_chars].rsplit(" ", 1)[0].rstrip()
        text = (clipped or text[:max_chars]) + "…"
    return text


def _wrap_to_width(draw, text, font, box_w):
    """Greedy word-wrap by MEASURED pixel width; hard-splits a word wider than the box."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if draw.textlength(trial, font=font) <= box_w:
            cur = trial
            continue
        if cur:
            lines.append(cur); cur = ""
        if draw.textlength(word, font=font) > box_w:
            piece = ""
            for ch in word:
                if draw.textlength(piece + ch, font=font) <= box_w:
                    piece += ch
                else:
                    if piece:
                        lines.append(piece)
                    piece = ch
            cur = piece
        else:
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _line_height(font):
    asc, desc = font.getmetrics()
    return int((asc + desc) * LINE_SPACING)


def fit_text_block(draw, text, font_path, box, max_lines, size_hi, size_lo):
    """Largest font size at which text wraps inside box (width, height, max_lines).
    If even size_lo overflows, wrap at size_lo, clip to max_lines, ellipsize last line."""
    for size in range(size_hi, size_lo - 1, -1):
        font = ImageFont.truetype(font_path, size)
        lines = _wrap_to_width(draw, text, font, box["w"])
        lh = _line_height(font)
        if len(lines) <= max_lines and len(lines) * lh <= box["h"]:
            return font, lines, lh
    font = ImageFont.truetype(font_path, size_lo)
    lh = _line_height(font)
    max_lines = max(1, min(max_lines, box["h"] // lh))
    lines = _wrap_to_width(draw, text, font, box["w"])
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > box["w"]:
            last = last[:-1].rstrip()
        lines[-1] = last + "…"
    return font, lines, lh


def render_thumbnail(template_path, out_dir, title, item_type, item_id,
                     brand_blue=DEFAULT_BRAND_BLUE, max_title_chars=50,
                     max_title_lines=3, font_path=None):
    """Stamp item TYPE (header, centered) + TITLE (footer, left) onto the template."""
    template_path = Path(template_path); out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    font_path = font_path or resolve_font_path()
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    type_text = " ".join((item_type or "").upper().split())
    if type_text:
        tfont, tlines, tlh = fit_text_block(draw, type_text, font_path, HEADER_BOX,
                                            2, TYPE_SIZE_HI, TYPE_SIZE_LO)
        y = HEADER_BOX["y"] + max(0, (HEADER_BOX["h"] - len(tlines) * tlh) // 2)
        for line in tlines:
            w = draw.textlength(line, font=tfont)
            x = HEADER_BOX["x"] + (HEADER_BOX["w"] - w) / 2
            draw.text((x, y), line, font=tfont, fill=brand_blue); y += tlh

    title_text = _cap_chars(title or "", max_title_chars)
    if title_text:
        ffont, flines, flh = fit_text_block(draw, title_text, font_path, FOOTER_BOX,
                                            max_title_lines, TITLE_SIZE_HI, TITLE_SIZE_LO)
        y = FOOTER_BOX["y"] + max(0, (FOOTER_BOX["h"] - len(flines) * flh) // 2)
        for line in flines:
            draw.text((FOOTER_BOX["x"], y), line, font=ffont, fill="white"); y += flh

    out_path = out_dir / "{}_thumbnail.png".format(item_id)
    img.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# AGOL helpers -- take an already-connected `gis` (this module never sees a password)
# ---------------------------------------------------------------------------
def _folder_name(f):
    if isinstance(f, dict):
        return f.get("title") or f.get("name")
    return getattr(f, "name", None) or getattr(f, "title", None)


def list_folder_titles(gis):
    me = gis.users.me
    return [n for n in (_folder_name(f) for f in (me.folders or [])) if n]


def iter_items(gis, scope, folders=None, item_type=None, max_items=2000):
    """Yield owned items. scope 'entire' = root + all folders; 'selected' = `folders`
    (use '(root)' for the root folder). item_type filters on exact Item.type."""
    me = gis.users.me
    want_type = (item_type or "").strip().lower()
    if scope == "entire":
        targets = [None] + list_folder_titles(gis)
    else:
        targets = [None if n == "(root)" else n for n in (folders or [])]
    seen, count = set(), 0
    for folder in targets:
        try:
            items = me.items(folder=folder, max_items=max_items)
        except Exception:
            items = []
        for it in items:
            if it.id in seen:
                continue
            seen.add(it.id)
            if want_type and (it.type or "").lower() != want_type:
                continue
            yield it
            count += 1
            if count >= max_items:
                return


_SCOPE_ALL = "Entire account (all folders incl. root)"
_SCOPE_SEL = "Selected folder(s)"


class Toolbox:
    def __init__(self):
        self.label = "Branded AGOL Thumbnails"
        self.alias = "brandedThumbnails"
        self.tools = [GenerateBrandedThumbnails]


class GenerateBrandedThumbnails:
    def __init__(self):
        self.label = "Generate Branded AGOL Thumbnails"
        self.description = (
            "Stamp a branded thumbnail (item type + title) onto every ArcGIS Online "
            "item you own, from one PNG template. Text auto-fits each band. Dry run "
            "renders locally without touching the portal."
        )
        self.canRunInBackground = False
        self.category = "AGOL"

    def getParameterInfo(self):
        template = arcpy.Parameter(
            displayName="Branding template (PNG)", name="template",
            datatype="DEFile", parameterType="Required", direction="Input")
        template.filter.list = ["png"]

        out_dir = arcpy.Parameter(
            displayName="Output folder (rendered PNGs)", name="out_dir",
            datatype="DEFolder", parameterType="Required", direction="Input")

        scope = arcpy.Parameter(
            displayName="Scope", name="scope",
            datatype="GPString", parameterType="Required", direction="Input")
        scope.filter.type = "ValueList"
        scope.filter.list = [_SCOPE_ALL, _SCOPE_SEL]
        scope.value = _SCOPE_ALL

        folders = arcpy.Parameter(
            displayName="Folders (when scope = selected; use (root) for root)",
            name="folders", datatype="GPString", parameterType="Optional",
            direction="Input", multiValue=True)
        folders.enabled = False

        item_type = arcpy.Parameter(
            displayName="Item type filter (optional; blank = all)", name="item_type",
            datatype="GPString", parameterType="Optional", direction="Input")

        max_chars = arcpy.Parameter(
            displayName="Max title characters", name="max_title_chars",
            datatype="GPLong", parameterType="Optional", direction="Input")
        max_chars.value = 50

        max_lines = arcpy.Parameter(
            displayName="Max title lines", name="max_title_lines",
            datatype="GPLong", parameterType="Optional", direction="Input")
        max_lines.value = 3

        dry_run = arcpy.Parameter(
            displayName="Dry run (render only -- do NOT update portal items)",
            name="dry_run", datatype="GPBoolean", parameterType="Optional",
            direction="Input")
        dry_run.value = True

        brand = arcpy.Parameter(
            displayName="Brand color (hex)", name="brand_color",
            datatype="GPString", parameterType="Optional", direction="Input")
        brand.value = DEFAULT_BRAND_BLUE

        max_items = arcpy.Parameter(
            displayName="Max items to process", name="max_items",
            datatype="GPLong", parameterType="Optional", direction="Input")
        max_items.value = 2000

        return [template, out_dir, scope, folders, item_type,
                max_chars, max_lines, dry_run, brand, max_items]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # Enable the folder picker only when scope = selected; populate it from AGOL.
        scope_p, folders_p = parameters[2], parameters[3]
        is_sel = scope_p.valueAsText == _SCOPE_SEL
        folders_p.enabled = is_sel
        if is_sel and not folders_p.filter.list:
            try:
                from arcgis.gis import GIS
                titles = ["(root)"] + list_folder_titles(GIS("pro"))
                folders_p.filter.type = "ValueList"
                folders_p.filter.list = titles
            except Exception:
                pass
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        from arcgis.gis import GIS

        template   = parameters[0].valueAsText
        out_dir    = parameters[1].valueAsText
        scope_lbl  = parameters[2].valueAsText
        folders    = parameters[3].values or None
        item_type  = parameters[4].valueAsText
        max_chars  = int(parameters[5].value or 50)
        max_lines  = int(parameters[6].value or 3)
        dry_run    = bool(parameters[7].value)
        brand      = parameters[8].valueAsText or DEFAULT_BRAND_BLUE
        max_items  = int(parameters[9].value or 2000)
        scope      = "entire" if scope_lbl == _SCOPE_ALL else "selected"

        gis = GIS("pro")
        messages.addMessage("Signed in as {}.".format(gis.users.me.username))
        messages.addMessage("Mode: {}".format("DRY RUN (no portal writes)" if dry_run
                                              else "LIVE (will update item thumbnails)"))

        rendered = updated = 0
        for it in iter_items(gis, scope, folders=folders,
                             item_type=item_type, max_items=max_items):
            try:
                png = render_thumbnail(template, out_dir, it.title, it.type, it.id,
                                       brand_blue=brand, max_title_chars=max_chars,
                                       max_title_lines=max_lines)
                rendered += 1
                if dry_run:
                    messages.addMessage("RENDERED: {} -> {}".format(it.title, png.name))
                else:
                    it.update(thumbnail=str(png))
                    updated += 1
                    messages.addMessage("UPDATED: {} ({})".format(it.title, it.type))
            except Exception as exc:
                messages.addWarningMessage("SKIPPED: {} -- {}".format(it.title, exc))

        tail = "" if dry_run else ", updated {}".format(updated)
        messages.addMessage("Done. Rendered {}{}.".format(rendered, tail))
        return

    def postExecute(self, parameters):
        return
