# -*- coding: utf-8 -*-
"""
Describe Feature Services -- standalone ArcGIS Pro Python toolbox.

Inventory ArcGIS Online hosted feature services into a data dictionary. Walks one
or many services and records, for each: item metadata, every layer/table, geometry
type, record count, spatial reference, and per-field name / alias / type / length /
nullability / domain (coded values OR range). Writes the log as TXT, CSV (flat, one
row per field), or multi-sheet XLSX (Services / Layers / Fields).

Scope the whole account, selected folders, a single service (item ID or URL), or a
name search. Authentication uses your active ArcGIS Pro sign-in -- GIS("pro") -- so
no credentials ever live in this file.

MAKE IT YOURS: everything is plain Python. The describe functions read an arcgis
FeatureLayer's `.properties` (a PropertyMap) but are written PropertyMap-OR-dict
tolerant, so the writers and serializers can be unit-tested with plain dicts (no
portal needed).

Runtime: arcgispro-py3 (ArcGIS Pro 3.x). Needs the ArcGIS API for Python (ships
with Pro) + openpyxl for XLSX output (also ships with Pro). Adapted from an
All Things Spatial workflow.

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
import csv
import datetime
import json
import os
from pathlib import Path

import arcpy


# ===========================================================================
# DESCRIBE CORE -- PropertyMap-OR-dict tolerant, so it unit-tests with plain
# dicts (no portal needed). Edit nothing here for a basic run.
# ===========================================================================
def _noop(*_a, **_k):
    pass


def _g(obj, key, default=None):
    """Get `key` from a dict OR an attribute-style object (arcgis PropertyMap)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def describe_field(f):
    """One field -> a flat dict, with domain flattened to a readable string."""
    domain = _g(f, "domain")
    dtype = dname = dvalues = ""
    if domain:
        dtype = _g(domain, "type", "") or ""
        dname = _g(domain, "name", "") or ""
        if "codedValue" in dtype or _g(domain, "codedValues"):
            pairs = _g(domain, "codedValues", []) or []
            dtype = "codedValue"
            dvalues = "; ".join("{}={}".format(_g(cv, "code"), _g(cv, "name")) for cv in pairs)
        elif "range" in dtype or _g(domain, "range"):
            rng = _g(domain, "range", []) or []
            dtype = "range"
            dvalues = "min={}, max={}".format(*(rng + ["", ""])[:2])
    return {
        "name": _g(f, "name", ""),
        "alias": _g(f, "alias", ""),
        "type": str(_g(f, "type", "")).replace("esriFieldType", ""),
        "length": _g(f, "length", ""),
        "nullable": _g(f, "nullable", ""),
        "domainType": dtype,
        "domainName": dname,
        "domainValues": dvalues,
    }


def describe_layer(layer, kind="layer", count_records=True, say=_noop):
    """One FeatureLayer/Table -> dict. `layer` needs `.properties` and (for counts)
    a `.query(return_count_only=True)` method."""
    p = _g(layer, "properties", layer)        # tolerate being handed props directly
    extent = _g(p, "extent")
    wkid = _g(_g(extent, "spatialReference"), "latestWkid") or \
        _g(_g(extent, "spatialReference"), "wkid")
    count = ""
    if count_records:
        try:
            count = layer.query(where="1=1", return_count_only=True)
        except Exception as e:  # noqa: BLE001
            say("    (count failed: {})".format(e))
            count = "n/a"
    fields = _g(p, "fields", []) or []
    return {
        "name": _g(p, "name", ""),
        "id": _g(p, "id", ""),
        "kind": kind,
        "geometryType": str(_g(p, "geometryType", "") or "").replace("esriGeometryType", "").replace("esriGeometry", ""),
        "recordCount": count,
        "wkid": wkid or "",
        "fieldCount": len(fields),
        "fields": [describe_field(f) for f in fields],
    }


def describe_item(item, count_records=True, say=_noop):
    """An arcgis Item (hosted feature service) -> dict incl. each layer + table."""
    say("Describing: {} ({})".format(_g(item, "title", "?"), _g(item, "id", "?")))
    layers = []
    for lyr in (getattr(item, "layers", None) or []):
        layers.append(describe_layer(lyr, "layer", count_records, say))
    for tbl in (getattr(item, "tables", None) or []):
        layers.append(describe_layer(tbl, "table", count_records, say))
    return {
        "title": _g(item, "title", ""),
        "id": _g(item, "id", ""),
        "owner": _g(item, "owner", ""),
        "type": _g(item, "type", ""),
        "url": _g(item, "url", ""),
        "created": _epoch(_g(item, "created")),
        "modified": _epoch(_g(item, "modified")),
        "access": _g(item, "access", ""),
        "tags": ", ".join(_g(item, "tags", []) or []),
        "snippet": _g(item, "snippet", "") or "",
        "layers": layers,
    }


def _epoch(ms):
    """AGOL stores ms-epoch; return an ISO date (or '')."""
    try:
        return datetime.datetime.fromtimestamp(int(ms) / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------------------
# Gather the target services per scope -- take an already-connected `gis`
# (this toolbox never sees a password)
# ---------------------------------------------------------------------------
_FS_TYPES = ("Feature Service", "Feature Layer")


def _is_feature_service(item):
    return _g(item, "type", "") in _FS_TYPES


def gather_services(gis, scope, folders=None, item_id_or_url=None,
                    search_query=None, max_items=500):
    """Return a list of feature-service Items per scope:
    'entire' | 'folders' | 'single' | 'search'. A non-empty item_id_or_url always
    wins (direct selection of one service, owned or not)."""
    # Direct id / URL override -- highest priority.
    if item_id_or_url:
        token = item_id_or_url.strip()
        item = None
        if token.lower().startswith("http"):
            item = _item_from_url(gis, token)
        else:
            item = gis.content.get(token)
        return [item] if item else []

    me = gis.users.me
    if scope == "search":
        text = (search_query or "").replace('"', "").strip()
        q = 'title:"{}" owner:{}'.format(text, me.username) if text else "owner:{}".format(me.username)
        items = gis.content.search(q, item_type="Feature *", max_items=max_items)
        return [it for it in items if _is_feature_service(it)]

    if scope == "single":
        return []   # handled via item_id_or_url upstream

    # entire / folders -> walk owner items by folder
    if scope == "folders":
        targets = [None if f == "(root)" else f for f in (folders or [])]
    else:
        names = [f.get("title") if isinstance(f, dict) else getattr(f, "name", None)
                 for f in (me.folders or [])]
        # root is already the None entry; 2.4.x also lists it as "Root Folder"
        targets = [None] + [n for n in names if n != "Root Folder"]
    out, seen = [], set()
    for folder in targets:
        try:
            items = me.items(folder=folder, max_items=max_items)
        except Exception:
            items = []
        for it in items:
            if it.id not in seen and _is_feature_service(it):
                seen.add(it.id)
                out.append(it)
                if len(out) >= max_items:
                    return out
    return out


def _item_from_url(gis, url):
    """Best-effort: resolve a service URL to its portal Item."""
    try:
        from arcgis.features import FeatureLayerCollection
        flc = FeatureLayerCollection(url, gis)
        if getattr(flc, "properties", None) is not None:
            sid = _g(flc.properties, "serviceItemId")
            if sid:
                return gis.content.get(sid)
    except Exception:
        pass
    return None


def _folder_name(f):
    """Pull a folder's display name across API shapes (dict with 'title'/'name',
    or a Folder object with .name/.title)."""
    if isinstance(f, dict):
        return f.get("title") or f.get("name")
    return getattr(f, "name", None) or getattr(f, "title", None)


def folder_titles(gis):
    """['(root)', <your AGOL folder titles...>] from the active sign-in."""
    titles = ["(root)"]
    try:
        for f in (gis.users.me.folders or []):
            name = _folder_name(f)
            if name and name != "Root Folder":   # root is already "(root)"
                titles.append(name)
    except Exception:
        return ["(root)"]
    return titles


# ---------------------------------------------------------------------------
# Writers -- TXT / CSV / multi-sheet XLSX
# ---------------------------------------------------------------------------
def _field_rows(report):
    """Flatten report -> one row per field (for CSV / the Fields sheet)."""
    rows = []
    for svc in report["services"]:
        for lyr in svc["layers"]:
            for f in lyr["fields"]:
                rows.append({
                    "service_title": svc["title"], "service_id": svc["id"],
                    "layer_name": lyr["name"], "layer_kind": lyr["kind"],
                    "geometryType": lyr["geometryType"], "recordCount": lyr["recordCount"],
                    "field_name": f["name"], "alias": f["alias"], "type": f["type"],
                    "length": f["length"], "nullable": f["nullable"],
                    "domainType": f["domainType"], "domainName": f["domainName"],
                    "domainValues": f["domainValues"],
                })
    return rows


_FIELD_COLS = ["service_title", "service_id", "layer_name", "layer_kind",
               "geometryType", "recordCount", "field_name", "alias", "type",
               "length", "nullable", "domainType", "domainName", "domainValues"]


def write_csv(report, path):
    rows = _field_rows(report)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=_FIELD_COLS)
        w.writeheader()
        w.writerows(rows)
    return path


def write_txt(report, path):
    L = []
    L.append("ArcGIS Online Feature Service Inventory")
    L.append("Generated: {}   Portal: {}".format(report["generated"], report.get("portal", "")))
    L.append("Services: {}".format(len(report["services"])))
    for svc in report["services"]:
        L.append("\n" + "=" * 72)
        L.append("{}  [{}]".format(svc["title"], svc["type"]))
        L.append("  id={}  owner={}  access={}".format(svc["id"], svc["owner"], svc["access"]))
        L.append("  created={}  modified={}".format(svc["created"], svc["modified"]))
        if svc["url"]:
            L.append("  url={}".format(svc["url"]))
        if svc["tags"]:
            L.append("  tags={}".format(svc["tags"]))
        for lyr in svc["layers"]:
            L.append("\n  -- {} '{}' (id {}) --".format(lyr["kind"], lyr["name"], lyr["id"]))
            L.append("     geometry={}  records={}  wkid={}  fields={}".format(
                lyr["geometryType"] or "n/a", lyr["recordCount"], lyr["wkid"], lyr["fieldCount"]))
            for f in lyr["fields"]:
                line = "       - {} ({}) {}".format(
                    f["name"], f["type"], "[{}]".format(f["alias"]) if f["alias"] else "")
                meta = []
                if f["length"]:
                    meta.append("len={}".format(f["length"]))
                meta.append("nullable={}".format(f["nullable"]))
                if f["domainType"]:
                    meta.append("domain={}:{}".format(f["domainType"], f["domainName"]))
                line += "  " + ", ".join(meta)
                L.append(line)
                if f["domainValues"]:
                    L.append("           values: {}".format(f["domainValues"]))
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


def write_xlsx(report, path):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    bold = Font(bold=True)

    ws = wb.active
    ws.title = "Services"
    svc_cols = ["title", "id", "owner", "type", "access", "created", "modified",
                "layerCount", "url", "tags"]
    ws.append(svc_cols)
    for c in ws[1]:
        c.font = bold
    for svc in report["services"]:
        ws.append([svc["title"], svc["id"], svc["owner"], svc["type"], svc["access"],
                   svc["created"], svc["modified"], len(svc["layers"]), svc["url"], svc["tags"]])

    wl = wb.create_sheet("Layers")
    lyr_cols = ["service_title", "service_id", "layer_name", "kind",
                "geometryType", "recordCount", "wkid", "fieldCount"]
    wl.append(lyr_cols)
    for c in wl[1]:
        c.font = bold
    for svc in report["services"]:
        for lyr in svc["layers"]:
            wl.append([svc["title"], svc["id"], lyr["name"], lyr["kind"],
                       lyr["geometryType"], lyr["recordCount"], lyr["wkid"], lyr["fieldCount"]])

    wf = wb.create_sheet("Fields")
    wf.append(_FIELD_COLS)
    for c in wf[1]:
        c.font = bold
    for row in _field_rows(report):
        wf.append([row[k] for k in _FIELD_COLS])

    for sheet in wb.worksheets:
        for col in sheet.columns:
            width = min(60, max(10, max((len(str(c.value)) for c in col if c.value is not None), default=10) + 2))
            sheet.column_dimensions[col[0].column_letter].width = width

    wb.save(path)
    return path


def write_report(report, out_path, fmt):
    """fmt in {'TXT','CSV','XLSX'}; returns the written path."""
    fmt = (fmt or "TXT").upper()
    if fmt == "CSV":
        return write_csv(report, out_path)
    if fmt == "XLSX":
        return write_xlsx(report, out_path)
    return write_txt(report, out_path)


def build_report(gis, services, count_records=True, say=_noop):
    """Describe a list of items -> the report dict the writers consume."""
    return {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "portal": _g(getattr(gis, "properties", None), "portalName", ""),
        "services": [describe_item(it, count_records, say) for it in services if it],
    }


def dumps(report):
    """Convenience for ad-hoc/manual JSON dumps (handy in tests)."""
    return json.dumps(report, indent=2, default=str)


# ===========================================================================
# TOOLBOX
# ===========================================================================
_DS_ALL = "Entire account (all folders)"
_DS_FOLDERS = "Selected folder(s)"
_DS_ONE = "Single service (item ID or URL)"
_DS_SEARCH = "Search by name"


class Toolbox:
    def __init__(self):
        self.label = "Describe Feature Services"
        self.alias = "describeFeatureServices"
        self.tools = [DescribeFeatureServices]


class DescribeFeatureServices:
    def __init__(self):
        self.label = "Describe Feature Services"
        self.description = (
            "Inventory ArcGIS Online feature services -- fields, types, domains, "
            "record counts, spatial reference, item metadata -- to a TXT, CSV, or "
            "multi-sheet XLSX log. Scope the whole account, selected folders, a "
            "single service (item ID or URL), or a name search."
        )
        self.canRunInBackground = False
        self.category = "AGOL"

    def getParameterInfo(self):
        # 0 -- scope
        scope = arcpy.Parameter(
            displayName="Scope", name="scope",
            datatype="GPString", parameterType="Required", direction="Input")
        scope.filter.type = "ValueList"
        scope.filter.list = [_DS_ALL, _DS_FOLDERS, _DS_ONE, _DS_SEARCH]
        scope.value = _DS_ALL

        # 1 -- folders (Selected folder(s))
        folders = arcpy.Parameter(
            displayName="Folders (when scope = Selected folder(s); use (root) for root)",
            name="folders", datatype="GPString", parameterType="Optional",
            direction="Input", multiValue=True)
        folders.filter.type = "ValueList"
        folders.enabled = False

        # 2 -- direct item id / service URL (Single service)
        id_or_url = arcpy.Parameter(
            displayName="Item ID or service URL (when scope = Single service)",
            name="id_or_url", datatype="GPString",
            parameterType="Optional", direction="Input")
        id_or_url.enabled = False

        # 3 -- search query (Search by name)
        query = arcpy.Parameter(
            displayName="Search text (when scope = Search by name)", name="query",
            datatype="GPString", parameterType="Optional", direction="Input")
        query.enabled = False

        # 4 -- output folder
        out_folder = arcpy.Parameter(
            displayName="Output folder (log file)", name="out_folder",
            datatype="DEFolder", parameterType="Required", direction="Input")

        # 5 -- output format
        out_format = arcpy.Parameter(
            displayName="Log format", name="out_format",
            datatype="GPString", parameterType="Required", direction="Input")
        out_format.filter.type = "ValueList"
        out_format.filter.list = ["XLSX", "CSV", "TXT"]
        out_format.value = "XLSX"

        # 6 -- output name (blank = auto)
        out_name = arcpy.Parameter(
            displayName="Log file name (optional; blank = auto)", name="out_name",
            datatype="GPString", parameterType="Optional", direction="Input")

        # 7 -- count records (a query per layer; can be slow on huge services)
        count_records = arcpy.Parameter(
            displayName="Count records (one query per layer)", name="count_records",
            datatype="GPBoolean", parameterType="Optional", direction="Input")
        count_records.value = True

        # 8 -- max items
        max_items = arcpy.Parameter(
            displayName="Max services to process", name="max_items",
            datatype="GPLong", parameterType="Optional", direction="Input")
        max_items.value = 500

        # 9 -- derived output path
        out_path = arcpy.Parameter(
            displayName="Log file written", name="out_path",
            datatype="DEFile", parameterType="Derived", direction="Output")

        return [scope, folders, id_or_url, query, out_folder,
                out_format, out_name, count_records, max_items, out_path]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # Enable only the input relevant to the chosen scope; populate the folder
        # picker from the active Pro sign-in the first time it's needed.
        scope = parameters[0].value
        parameters[1].enabled = scope == _DS_FOLDERS
        parameters[2].enabled = scope == _DS_ONE
        parameters[3].enabled = scope == _DS_SEARCH
        if parameters[1].enabled and len(list(parameters[1].filter.list or [])) <= 1:
            try:
                from arcgis.gis import GIS
                parameters[1].filter.list = folder_titles(GIS("pro"))
            except Exception:
                pass
        return

    def updateMessages(self, parameters):
        if parameters[0].value == _DS_SEARCH and not parameters[3].valueAsText \
                and not parameters[2].valueAsText:
            parameters[3].setWarningMessage("Enter search text, or use an Item ID / URL.")
        return

    def execute(self, parameters, messages):
        from arcgis.gis import GIS

        scope_label = parameters[0].value
        folders = list(parameters[1].values) if parameters[1].values else []
        id_or_url = parameters[2].valueAsText
        query = parameters[3].valueAsText
        out_folder = parameters[4].valueAsText
        out_format = parameters[5].value
        out_name = parameters[6].valueAsText
        count_records = bool(parameters[7].value)
        max_items = int(parameters[8].value or 500)

        scope = {_DS_FOLDERS: "folders", _DS_ONE: "single",
                 _DS_SEARCH: "search"}.get(scope_label, "entire")

        # Sign in with the active ArcGIS Pro session -- no credentials in this file.
        gis = GIS("pro")
        messages.addMessage("Signed in as {} ({})".format(
            gis.users.me.username, gis.properties.portalName))

        services = gather_services(
            gis, scope, folders=folders, item_id_or_url=id_or_url,
            search_query=query, max_items=max_items)
        messages.addMessage("{} feature service(s) to describe.".format(len(services)))
        if not services:
            raise arcpy.ExecuteError("No feature services matched the chosen scope.")

        report = build_report(gis, services, count_records=count_records,
                              say=messages.addMessage)

        ext = {"XLSX": ".xlsx", "CSV": ".csv", "TXT": ".txt"}[out_format]
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        base = out_name or "agol_inventory_{}".format(stamp)
        out_path = os.path.join(out_folder, base + ext)
        write_report(report, out_path, out_format)

        messages.addMessage("\nLog written: {}".format(out_path))
        parameters[9].value = out_path
        return

    def postExecute(self, parameters):
        return
