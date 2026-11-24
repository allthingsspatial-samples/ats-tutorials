# Headless test for "Describe Feature Services" and "Generate Branded Thumbnails" (episode A7). OFFLINE: a fake
# portal object stands in for GIS("pro"), so the test needs no sign-in and changes nothing online. It checks the
# search scope (owner only, folder, root folder, tag), the CSV report, the 600 x 400 PNGs, preview-only vs update,
# the dialog (folder list filled, sign-in error, update warning) and that the toolbox still loads every tool.
# Run with the ArcGIS Pro Python:  propy.bat tests\test_agol_tools.py      Exit code 0 = PASS.
import os, sys, shutil, csv, importlib.machinery, importlib.util
import arcpy
sys.dont_write_bytecode = True   # loading the .pyt as a module below must not leave __pycache__ in the toolbox folder

HERE = os.path.dirname(os.path.abspath(__file__))
PYT = os.path.join(os.path.dirname(HERE), "ATS-Starter.pyt")
S = os.path.join(HERE, "_scratch", "agol_tools")
fails = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg, flush=True)
    if not cond: fails.append(msg)


if os.path.exists(S): shutil.rmtree(S)
os.makedirs(S)


# ---- a fake portal (only the parts of the ArcGIS API for Python the tools use) ----------------
class Layer:
    def __init__(self, name, geom, n, nfields, caps="Query"):
        self.properties = {"name": name, "geometryType": geom, "fields": [{}] * nfields, "capabilities": caps}
        self._n = n

    def query(self, where="1=1", return_count_only=False):
        assert return_count_only
        return self._n


class Level:
    def __init__(self, n): self.name = n


class Sharing:
    def __init__(self, n): self.sharing_level = Level(n)


class Item:
    def __init__(self, iid, title, owner, folder, tags, layers, tables=(), level="PRIVATE"):
        self.id, self.title, self.owner, self.ownerFolder, self.tags = iid, title, owner, folder, tags
        self.layers, self.tables = list(layers), list(tables)
        self.sharing = Sharing(level)
        self.modified, self.size, self.thumbnail, self.type = 1794984403000, 180224, None, "Feature Service"
        self.updated_with = None

    def update(self, item_properties=None, data=None, thumbnail=None, metadata=None):
        self.updated_with = thumbnail
        self.thumbnail = "thumbnail/" + os.path.basename(thumbnail)
        return True


ME = "demo_user"
ITEMS = [
    Item("a1", "Test - County Boundaries", ME, "f1", ["ATS-A7-test"], [Layer("Counties", "esriGeometryPolygon", 3, 6)]),
    Item("a2", "Test - Transmission Lines", ME, "f1", ["ats-a7-TEST"], [Layer("Lines", "esriGeometryPolyline", 138, 9, "Create,Delete,Query,Update,Editing")]),
    Item("a3", "Root Points", ME, None, ["other"], [Layer("Pts", "esriGeometryPoint", 5, 3)], [Layer("Lookup", None, 7, 2)], "PUBLIC"),
    Item("x9", "Someone Else", "other_user", None, ["ATS-A7-test"], [Layer("X", "esriGeometryPoint", 1, 1)]),
]


class Folder:
    def __init__(self, fid, name): self.name, self.properties = name, {"id": fid, "name": name}

    def list(self, item_type=None):
        return iter([i for i in ITEMS if i.ownerFolder == self.properties["id"] and i.type == item_type])


class Me:
    username = ME
    @property
    def folders(self): return iter([Folder("f1", "Tests"), Folder("f2", "Empty")])


class Users:
    me = Me()


class Content:
    def __init__(self): self.queries = []

    def search(self, query, item_type=None, max_items=100):
        self.queries.append((query, item_type))
        # The real search is limited by "owner:"; the fake returns everything so the tools' own owner check is tested.
        return [i for i in ITEMS if i.type == item_type][:max_items]


class FakeGIS:
    users = Users()
    content = Content()


# ---- the module, the way Pro loads it -----------------------------------------------------------
loader = importlib.machinery.SourceFileLoader("ats_starter_mod", PYT)
spec = importlib.util.spec_from_loader("ats_starter_mod", loader)
mod = importlib.util.module_from_spec(spec); loader.exec_module(mod)
gis = FakeGIS()

titles = lambda items: [i.title for i in items]
check(titles(mod.find_my_feature_services(gis)) == ["Root Points", "Test - County Boundaries", "Test - Transmission Lines"],
      "all folders: only my 3 items, sorted, never another owner's item")
check(gis.content.queries[-1] == ("owner:demo_user", "Feature Service"), "search query is owner:<me>, type Feature Service")
mod.find_my_feature_services(gis, None, "ATS-A7-test")
check(gis.content.queries[-1][0] == 'owner:demo_user AND tags:"ATS-A7-test"', "a tag narrows the portal search too")
check(titles(mod.find_my_feature_services(gis, "Tests")) == ["Test - County Boundaries", "Test - Transmission Lines"], "folder Tests: 2 items")
check(titles(mod.find_my_feature_services(gis, mod.ROOT_FOLDER)) == ["Root Points"], "root folder: 1 item")
check(titles(mod.find_my_feature_services(gis, None, "ATS-A7-TEST")) == ["Test - County Boundaries", "Test - Transmission Lines"],
      "tag filter is not case sensitive and skips the other owner's tagged item")
check(mod.find_my_feature_services(gis, "Empty") == [], "empty folder: no items")
try:
    mod.find_my_feature_services(gis, "Nope"); check(False, "unknown folder raises")
except ValueError as e:
    check("no folder named Nope" in str(e), "unknown folder raises a clear ValueError")

# Describe Feature Services
out_csv = os.path.join(S, "report.csv")
r = mod.describe_feature_services(gis, out_csv)
rows = list(csv.DictReader(open(out_csv, encoding="utf-8-sig")))
check(r["services"] == 3 and r["layers"] == 4 and r["features"] == 3 + 138 + 5 + 7, "describe: 3 services, 4 layers (incl. a table), 153 features")
check(list(rows[0].keys()) == mod.REPORT_COLUMNS, "CSV columns = REPORT_COLUMNS")
by = {x["layer"]: x for x in rows}
check(by["Lines"]["geometry"] == "Polyline" and by["Lines"]["features"] == "138" and by["Lines"]["fields"] == "9", "Lines row: Polyline, 138 features, 9 fields")
check(by["Lines"]["editable"] == "yes" and by["Counties"]["editable"] == "no", "editable from layer capabilities")
check(by["Lookup"]["geometry"] == "table", "a table is reported as geometry 'table'")
check("folder" not in rows[0], "no folder column in the report (privacy on screen)")
check(by["Pts"]["sharing"] == "public" and by["Counties"]["sharing"] == "private", "sharing level from item.sharing")
check(by["Counties"]["thumbnail"] == "no" and by["Counties"]["size_kb"] == "176", "thumbnail flag and size in KB")
check(all(x["item_id"] != "x9" for x in rows), "the other owner's item is not in the report")

# Generate Branded Thumbnails: preview only, then update
from PIL import Image
pv = os.path.join(S, "preview"); os.makedirs(pv)
g1 = mod.generate_branded_thumbnails(gis, pv, "Tests", None, "All Things Spatial", "Navy", update=False)
check(len(g1["pngs"]) == 2 and g1["updated"] == 0, "preview: 2 PNGs, 0 updated")
check(all(i.updated_with is None for i in ITEMS), "preview: no item was changed")
sizes = {Image.open(p).size for p in g1["pngs"]}
check(sizes == {(600, 400)}, "PNGs are 600 x 400 (%s)" % sizes)
check(sorted(os.listdir(pv)) == ["Test - County Boundaries.png", "Test - Transmission Lines.png"], "PNG names from the item titles, nothing else written")
long_png = mod.render_thumbnail("A very long hosted feature layer title that has to wrap over several lines to fit the card",
                                "1 layer | 12,345 features", os.path.join(S, "long.png"), geometry="Point", colors="Forest")
check(Image.open(long_png).size == (600, 400), "a long title still renders at 600 x 400")
very_long = mod.render_thumbnail(" ".join(["Word%d" % i for i in range(60)]), "x", os.path.join(S, "very_long.png"))
check(Image.open(very_long).size == (600, 400), "a 60-word title is cut with an ellipsis and still renders")
up = os.path.join(S, "update"); os.makedirs(up)
g2 = mod.generate_branded_thumbnails(gis, up, None, "ATS-A7-test", update=True)
check(g2["updated"] == 2, "update: 2 thumbnails updated")
check(ITEMS[0].updated_with and ITEMS[1].updated_with and ITEMS[2].updated_with is None and ITEMS[3].updated_with is None,
      "update: only the 2 matching items I own were changed")
check(mod.describe_item(ITEMS[0])[0]["thumbnail"] == "yes", "describe after update: thumbnail yes")

# The dialog: folder value list, sign-in error, update warning (portal faked through the module cache)
mod._PORTAL.clear(); mod._PORTAL["gis"] = gis
t = mod.GenerateBrandedThumbnails(); P = t.getParameterInfo()
check([p.name for p in P] == ["folder", "tag", "out_folder", "footer", "colors", "update_items", "updated_count"], "thumbnail tool parameters")
check(P[5].value is False and P[3].value == "All Things Spatial", "defaults: preview only, footer text")
t.updateParameters(P); t.updateMessages(P)
check(list(P[0].filter.list) == [mod.ALL_FOLDERS, mod.ROOT_FOLDER, "Empty", "Tests"], "Folder list filled from my folders")
check(not P[0].hasError(), "no sign-in error when the portal answers")
P[5].value = True; t.updateMessages(P)
check(P[5].hasWarning() and "replaces the thumbnail" in P[5].message, "update checked: warning shown")
mod._PORTAL.clear()
mod._PORTAL["folders"] = (None, "Sign in to ArcGIS Online in ArcGIS Pro first (RuntimeError).")
D = mod.DescribeFeatureServices(); Q = D.getParameterInfo()
D.updateParameters(Q); D.updateMessages(Q)
check(Q[0].hasError() and "Sign in to ArcGIS Online" in Q[0].message, "not signed in: error on Folder")
check([q.name for q in Q] == ["folder", "tag", "out_csv", "service_count"] and Q[3].parameterType == "Derived", "describe tool parameters")
mod._PORTAL.clear()

# The toolbox still loads every tool
arcpy.ImportToolbox(PYT)
for name in ("BatchClipByFeatureClass", "PrecheckFeatureClasses", "FindScriptPaths", "ExportFeaturesToFolder",
             "ExportProSymbols", "DescribeFeatureServices", "GenerateBrandedThumbnails", "CopyMeTemplate"):
    check(hasattr(arcpy, name + "_atsstarter"), "toolbox exposes %s_atsstarter" % name)

print("RESULT", "PASS" if not fails else "FAIL %d" % len(fails))
sys.exit(1 if fails else 0)
