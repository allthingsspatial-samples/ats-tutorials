# -*- coding: utf-8 -*-
"""Audit da Cursor Scope - an ArcGIS Pro Python toolbox.

Use case: you are planning the move to ArcGIS Pro 3.7 and you have years of accumulated .py
scripts, .pyt toolboxes and notebooks. Pro 3.7 invalidates an arcpy.da cursor when its `with`
block exits, so any script that called reset() or re-iterated the cursor afterwards worked
before the upgrade and raises ValueError: I/O operation on closed file after it.

Point this at your scripts folder BEFORE you schedule the upgrade and it returns the files and
line numbers to review. It parses source with the standard-library ast module and executes
nothing, so it is safe to run against code you have not read.

Findings are a review list, not a verdict. See the limits noted in scan_source below.

Add this file to a project as a toolbox and run the tool. MIT licensed.
"""
from __future__ import annotations

import arcpy


import ast
import json
from pathlib import Path

CURSOR_CLASSES = {"SearchCursor", "UpdateCursor", "InsertCursor"}
SCAN_SUFFIXES = {".py", ".pyt", ".ipynb"}
SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


# --------------------------------------------------------------------------- alias discovery
class _Aliases(ast.NodeVisitor):
    """Names that refer to arcpy.da, and names bound directly to a cursor class."""

    def __init__(self) -> None:
        self.da_names = {"da"}
        self.direct: dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            if a.name in ("arcpy.da",) and a.asname:
                self.da_names.add(a.asname)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        for a in node.names:
            if mod == "arcpy" and a.name == "da":
                self.da_names.add(a.asname or "da")
            elif mod in ("arcpy.da", "da") and a.name in CURSOR_CLASSES:
                self.direct[a.asname or a.name] = a.name
        self.generic_visit(node)


def _cursor_class(call: ast.AST, al: _Aliases) -> str | None:
    if not isinstance(call, ast.Call):
        return None
    fn = call.func
    if isinstance(fn, ast.Attribute) and fn.attr in CURSOR_CLASSES:
        owner = fn.value
        if isinstance(owner, ast.Attribute) and owner.attr == "da":
            return fn.attr                                  # arcpy.da.SearchCursor
        if isinstance(owner, ast.Name) and owner.id in al.da_names:
            return fn.attr                                  # da.SearchCursor / da2.SearchCursor
    if isinstance(fn, ast.Name) and fn.id in al.direct:
        return al.direct[fn.id]                             # SearchCursor / SC
    return None


# --------------------------------------------------------------------------- scope splitting
def _own_nodes(scope: ast.AST):
    """Walk a scope without descending into nested scopes, which have their own names."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, SCOPE_NODES):
            stack.extend(ast.iter_child_nodes(node))


def _bindings(scope: ast.AST) -> dict[str, list[int]]:
    """Every line in this scope where a name is bound. Missing a binding form causes a false
    positive, so this covers the ones that actually appear in scripts."""
    out: dict[str, list[int]] = {}

    def add(name: str, line: int) -> None:
        out.setdefault(name, []).append(line)

    # parameters exist from the first line of the scope
    args = getattr(scope, "args", None)
    if args is not None:
        for a in (*args.posonlyargs, *args.args, *args.kwonlyargs,
                  args.vararg, args.kwarg):
            if a is not None:
                add(a.arg, getattr(scope, "lineno", 0))

    for node in _own_nodes(scope):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        add(n.id, node.lineno)
        elif isinstance(node, (ast.For, ast.AsyncFor)):   # NOT ast.comprehension - it does not leak
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    add(n.id, getattr(node, "lineno", getattr(node.target, "lineno", 0)))
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    for n in ast.walk(item.optional_vars):
                        if isinstance(n, ast.Name):
                            add(n.id, node.lineno)
        elif isinstance(node, ast.NamedExpr):
            if isinstance(node.target, ast.Name):
                add(node.target.id, node.lineno)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            add(node.name, node.lineno)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                add((a.asname or a.name).split(".")[0], node.lineno)
        elif isinstance(node, SCOPE_NODES) and hasattr(node, "name"):
            add(node.name, node.lineno)
    return out


def _end_line(node: ast.AST) -> int:
    end = getattr(node, "end_lineno", None)
    return end or max((getattr(n, "lineno", 0) for n in ast.walk(node)), default=0)


def _scan_scope(scope: ast.AST, al: _Aliases, origin: str, locate) -> list[dict]:
    binds = _bindings(scope)
    loads = [(n.id, n.lineno) for n in _own_nodes(scope)
             if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)]
    found: list[dict] = []
    for node in _own_nodes(scope):
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        for item in node.items:
            cls = _cursor_class(item.context_expr, al)
            if not cls or not isinstance(item.optional_vars, ast.Name):
                continue
            name = item.optional_vars.id
            end = _end_line(node)
            nxt = min((ln for ln in binds.get(name, []) if ln > end), default=None)
            for used, line in loads:
                if used != name or line <= end:
                    continue
                if nxt is not None and line >= nxt:
                    continue
                where, wline = locate(line)
                endwhere, endline = locate(end)
                # In a notebook the block can close in a DIFFERENT cell from the use - naming only
                # a line number there would send the reader to the wrong place.
                closed = f"line {endline}" if endwhere in ("", where) else f"{endwhere} line {endline}"
                found.append({"origin": origin, "where": where, "line": wline,
                              "name": name, "kind": cls,
                              "detail": f"used at line {wline}; its `with` block closed at {closed}"})
    return found


def scan_source(src: str, origin: str, locate=None) -> list[dict]:
    """locate maps a line in `src` to (label, line) - used to report notebook cells."""
    locate = locate or (lambda ln: ("", ln))
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        where, wline = locate(exc.lineno or 1)
        return [{"origin": origin, "where": where, "line": wline, "name": "", "kind": "SYNTAX",
                 "detail": f"could not parse: {exc.msg}"}]
    al = _Aliases()
    al.visit(tree)
    scopes = [tree] + [n for n in ast.walk(tree) if isinstance(n, SCOPE_NODES)]
    out: list[dict] = []
    for sc in scopes:
        out += _scan_scope(sc, al, origin, locate)
    return out


# --------------------------------------------------------------------------- notebooks
def _notebook_unit(path: Path):
    """Join code cells into ONE parse unit. A notebook shares a namespace across cells, so a cursor
    opened in one cell and reset in the next is a real breakage - and it is invisible if each cell
    is parsed alone. Returns (source, locate) where locate maps a joined line to (cell label, line)."""
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return None, str(exc)
    if not isinstance(nb, dict) or not isinstance(nb.get("cells"), list):
        return None, "not a notebook: no top-level cells array"

    lines: list[str] = []
    index: list[tuple[str, int]] = []
    for pos, cell in enumerate(nb.get("cells", []), start=1):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        label = f"cell {pos}"
        cell_lines = src.splitlines()
        # A %%cell-magic makes the ENTIRE cell something other than Python, so blank all of it.
        # Blanking only the first line would leave a shell body to be parsed as Python, and because
        # cells are joined into one unit that single cell would fail the parse for the whole
        # notebook and hide every real finding in it.
        whole_cell_magic = bool(cell_lines) and cell_lines[0].lstrip().startswith("%%")
        for i, ln in enumerate(cell_lines, start=1):
            if whole_cell_magic or ln.lstrip().startswith(("%", "!")):
                lines.append("")          # keep the line count aligned with Jupyter's gutter
            else:
                lines.append(ln)
            index.append((label, i))
        lines.append("")            # separator so the last statement of a cell terminates
        index.append((label, len(src.splitlines()) + 1))

    def locate(ln: int):
        return index[ln - 1] if 1 <= ln <= len(index) else ("", ln)

    return "\n".join(lines), locate


def scan_path(root: Path, recurse: bool = True) -> list[dict]:
    root = Path(root)
    findings: list[dict] = []
    paths = [root] if root.is_file() else sorted(
        p for p in (root.rglob("*") if recurse else root.glob("*"))
        if p.suffix.lower() in SCAN_SUFFIXES)
    for p in paths:
        origin = str(p)                       # full path: two files can share a basename
        # A short form for the printed report. On a real scripts share the absolute paths are
        # long enough to push the finding off the right of the screen; the JSON keeps `origin`.
        try:
            rel = p.name if root.is_file() else str(p.relative_to(root))
        except ValueError:                    # not under root; should not happen, but do not crash
            rel = origin
        before = len(findings)
        if p.suffix.lower() == ".ipynb":
            src, locate = _notebook_unit(p)
            if src is None:
                findings.append({"origin": origin, "where": "", "line": 0, "name": "",
                                 "kind": "READ", "detail": f"unreadable notebook: {locate}"})
            else:
                findings += scan_source(src, origin, locate)
        else:
            try:
                findings += scan_source(p.read_text(encoding="utf-8", errors="replace"), origin)
            except OSError as exc:
                findings.append({"origin": origin, "where": "", "line": 0, "name": "",
                                 "kind": "READ", "detail": str(exc)})
        for f in findings[before:]:
            f["rel"] = rel
    return findings


def report(findings: list[dict], scanned: int | None = None, root=None) -> str:
    head = f"Scanned {scanned} file(s)." if scanned is not None else ""
    if not findings:
        return (f"{head} No cursor-after-block usage found in the shapes this tool understands.\n"
                "That is not a clean bill of health: cursors held in containers or attributes, and "
                "Python embedded in .atbx/.tbx toolboxes, are outside what it can see.").strip()
    out = [f"{head} {len(findings)} place(s) to review:".strip()]
    if root is not None:
        out.append(f"Paths below are relative to {root}")
    out.append("")
    def shown(f):
        return f.get("rel") or f["origin"]
    w = max(len(shown(f)) for f in findings)
    for f in sorted(findings, key=lambda f: (shown(f), f.get("where", ""), f["line"])):
        tag = f["kind"] if f["kind"] in CURSOR_CLASSES else f"[{f['kind']}]"
        where = f" {f['where']}" if f.get("where") else ""
        out.append(f"  {shown(f):<{w}}{where}  line {f['line']:>5}  {tag:<13} {f['detail']}")
    out += ["",
            "Each of these is a place to LOOK, not a confirmed bug - the check follows a name, so a",
            "name reused for something this tool cannot trace will appear here. Where the finding is",
            "real, at Pro 3.7 it raises ValueError: I/O operation on closed file. The fix is a fresh",
            "cursor for the second pass, or finishing the work inside the original `with` block."]
    return "\n".join(out)

class Toolbox(object):
    def __init__(self):
        self.label = "Cursor Scope Audit"
        self.alias = "cursorscope"
        self.tools = [AuditCursorScope]


class AuditCursorScope(object):
    def __init__(self):
        self.label = "Audit da Cursor Scope"
        self.description = (
            "Find arcpy.da cursors used after their `with` block closes - the pattern that stops "
            "working at ArcGIS Pro 3.7. Reports file and line for each place to review."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        target = arcpy.Parameter(
            displayName="Folder or file to scan", name="target",
            datatype=["DEFolder", "DEFile"], parameterType="Required", direction="Input")

        recurse = arcpy.Parameter(
            displayName="Include subfolders", name="recurse", datatype="GPBoolean",
            parameterType="Optional", direction="Input")
        recurse.value = True

        out_report = arcpy.Parameter(
            displayName="Write report to file (optional)", name="out_report",
            datatype="DEFile", parameterType="Optional", direction="Output")
        out_report.filter.list = ["txt", "json"]

        return [target, recurse, out_report]

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):
        target = Path(parameters[0].valueAsText)
        recurse = True if parameters[1].value is None else bool(parameters[1].value)
        out_path = parameters[2].valueAsText

        if not target.exists():
            arcpy.AddError("No such path: {}".format(target))
            return

        arcpy.AddMessage("Scanning {} ({} subfolders)".format(
            target, "including" if recurse else "excluding"))

        if target.is_file():
            scanned = 1
        else:
            it = target.rglob("*") if recurse else target.glob("*")
            scanned = sum(1 for p in it if p.suffix.lower() in SCAN_SUFFIXES)

        if scanned == 0:
            arcpy.AddError(
                "No .py, .pyt or .ipynb files found under {}. {}".format(
                    target,
                    "Tick 'Include subfolders' if they are nested." if not recurse
                    else "Check you are pointing at the right folder."))
            return

        findings = scan_path(target, recurse=recurse)
        text = report(findings, scanned=scanned, root=target)

        for line in text.splitlines():
            arcpy.AddMessage(line)
        if findings:
            arcpy.AddWarning(
                "{} place(s) to review before upgrading to Pro 3.7. These are locations to "
                "check, not confirmed failures.".format(len(findings)))

        if out_path:
            if out_path.lower().endswith(".json"):
                with open(out_path, "w", encoding="utf-8") as fh:
                    json.dump(findings, fh, indent=2)
            else:
                with open(out_path, "w", encoding="utf-8") as fh:
                    fh.write(text + "\n")
            arcpy.AddMessage("Report written to {}".format(out_path))
