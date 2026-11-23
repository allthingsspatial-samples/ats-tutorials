# -*- coding: utf-8 -*-
"""Enrich From Service - an ArcGIS Pro Python toolbox template.

Three-phase attribute enrichment: read a worklist with a SearchCursor and close it, call an
external service with NO cursor open, then write results back with a fresh UpdateCursor matching
on OID@. The same WHERE_CLAUSE drives the read and the write, which is what makes the job
restartable and what stops a metered service being billed for rows that already have values.

TO USE THIS TEMPLATE: edit the lookup() function marked below. Everything else is parameters.

Safety: the Dry run parameter defaults to checked and nothing is written until you clear it.
A where clause is required and a clause matching every row is refused. The row cap limits how
much one run can touch. Test against a copy of your data first - phase 3 rewrites rows.

MIT licensed.
"""
from __future__ import annotations

import arcpy


import json
from datetime import datetime, timezone

import arcpy

OID = "OID@"


class ConfigError(Exception):
    """Raised before any data is touched, so a bad configuration costs nothing."""


# ------------------------------------------------------------------ phase 0: refuse bad input
def preflight(fc, where_clause, read_fields, write_fields, max_rows):
    """Validate before touching data. Every check here exists because the failure it prevents is
    expensive, irreversible, or both."""
    if not fc:
        raise ConfigError("FEATURE_CLASS is required.")
    if not arcpy.Exists(fc):
        raise ConfigError(f"FEATURE_CLASS does not exist: {fc}")

    if not where_clause or not str(where_clause).strip():
        raise ConfigError(
            "WHERE_CLAUSE is required and has no default. It is what makes this job restartable "
            "and what stops you paying an external service for rows that already have values. "
            "Express the rows that still NEED work, for example: \"CITY IS NULL OR CITY = ''\"")
    if str(where_clause).strip().replace(" ", "") in ("1=1", "1<>0"):
        raise ConfigError(
            "WHERE_CLAUSE selects every row. If that is genuinely intended, say so explicitly in "
            "a clause that names the fields, so the intent survives the next person reading it.")

    if OID not in read_fields:
        raise ConfigError(f"{OID} must be the first read field - it is the join key between phases.")
    if OID not in write_fields:
        raise ConfigError(f"{OID} must be present in the write fields to match rows back.")

    existing = {f.name for f in arcpy.ListFields(fc)}
    for label, fields in (("read", read_fields), ("write", write_fields)):
        missing = [f for f in fields if f != OID and f not in existing]
        if missing:
            raise ConfigError(f"{label} field(s) not on {fc}: {', '.join(missing)}")

    if not isinstance(max_rows, int) or max_rows < 1:
        raise ConfigError("MAX_ROWS must be a positive integer. It caps the blast radius of a mistake.")
    return True


# ------------------------------------------------------------------ phase 1: read
def read_worklist(fc, where_clause, read_fields, max_rows):
    """Return a list of dicts, one per row needing work. The cursor is closed before this returns -
    nothing downstream may hold it."""
    work = []
    with arcpy.da.SearchCursor(fc, read_fields, where_clause=where_clause) as cur:
        for row in cur:
            work.append(dict(zip(read_fields, row)))
            if len(work) >= max_rows:
                break
    return work


# ------------------------------------------------------------------ phase 2: the slow part
def enrich(work, lookup):
    """Call `lookup` once per row and collect the results, keyed by OID.

    `lookup` is yours to supply: it receives one row dict and returns either a dict of
    {field_name: value} to write, or None to skip the row. It runs with NO cursor open, so it may
    take as long as it needs - a network call, a rate limit, a retry - without holding a lock on
    the table.
    """
    decisions, failed = {}, []
    for row in work:
        try:
            result = lookup(row)
        except Exception as exc:                      # one bad row must not end the run
            failed.append({"oid": row[OID], "error": f"{type(exc).__name__}: {exc}"})
            continue
        if result:
            decisions[row[OID]] = result
    return decisions, failed


# ------------------------------------------------------------------ phase 3: write
def write_back(fc, where_clause, write_fields, decisions, dry_run=True, only_if_empty=True):
    """Apply decisions by OID. A fresh cursor - the phase 1 cursor is long closed, and at ArcGIS
    Pro 3.7 reusing it would raise ValueError anyway."""
    planned, changed, skipped = [], 0, 0

    with arcpy.da.UpdateCursor(fc, write_fields, where_clause=where_clause) as cur:
        for row in cur:
            oid = row[0]
            decision = decisions.get(oid)
            if not decision:
                continue

            row_changes = {}
            for i, field in enumerate(write_fields):
                if field == OID or field not in decision:
                    continue
                current, proposed = row[i], decision[field]
                if proposed is None or proposed == current:
                    continue
                # Re-check emptiness inside the write pass. WHERE_CLAUSE already restricted the set,
                # but another editor may have filled the row since phase 1 read it.
                if only_if_empty and current not in (None, "", " "):
                    skipped += 1
                    continue
                row_changes[field] = {"from": current, "to": proposed}
                row[i] = proposed

            if not row_changes:
                continue
            planned.append({"oid": oid, "changes": row_changes})
            if not dry_run:
                cur.updateRow(row)
            changed += 1

    return {"planned": planned, "changed": changed, "skipped_not_empty": skipped,
            "dry_run": bool(dry_run)}


# ------------------------------------------------------------------ reporting
def summarize(work, decisions, failed, result, max_rows):
    lines = []
    mode = "DRY RUN - nothing was written" if result["dry_run"] else "LIVE - rows were updated"
    lines.append(f"{mode}")
    lines.append(f"  rows read (cap {max_rows:,})      {len(work):,}")
    lines.append(f"  rows the lookup answered         {len(decisions):,}")
    lines.append(f"  rows the lookup failed on        {len(failed):,}")
    lines.append(f"  rows with at least one change    {result['changed']:,}")
    lines.append(f"  values skipped, already set      {result['skipped_not_empty']:,}")
    if result["planned"]:
        lines.append("")
        lines.append("  first few changes:")
        for item in result["planned"][:5]:
            for field, ch in item["changes"].items():
                lines.append(f"    OID {item['oid']:<8} {field:<22} {ch['from']!r} -> {ch['to']!r}")
    if failed:
        lines.append("")
        lines.append("  first few failures:")
        for f in failed[:5]:
            lines.append(f"    OID {f['oid']:<8} {f['error']}")
    if work and not decisions and not failed:
        lines.append("")
        lines.append("  The lookup returned nothing for every row it was given. If you have not")
        lines.append("  replaced the lookup() stub yet, that is expected - the shipped stub always")
        lines.append("  returns None so the template runs end to end without contacting anything.")
    if result["dry_run"]:
        lines.append("")
        # Only invite a live run when there is something to apply. Printing this after a run that
        # planned nothing sends you to DRY_RUN = False for a job that would do exactly nothing.
        lines.append("  Set DRY_RUN = False to apply these changes." if result["planned"]
                     else "  Nothing to apply - this dry run planned no changes.")
    if len(work) == max_rows:
        lines.append("")
        lines.append(f"  NOTE: the run stopped at the MAX_ROWS cap of {max_rows:,}. There are likely")
        lines.append("  more rows matching WHERE_CLAUSE. Re-run to continue - the clause makes it resumable.")
    return "\n".join(lines)


def write_log(path, work, decisions, failed, result):
    """A JSON record of what happened, so a re-run can be diffed against the last one."""
    payload = {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": result["dry_run"], "rows_read": len(work),
        "rows_answered": len(decisions), "rows_changed": result["changed"],
        "skipped_not_empty": result["skipped_not_empty"],
        "planned": result["planned"], "failed": failed,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    return path


def run(fc, where_clause, read_fields, write_fields, lookup, max_rows=500,
        dry_run=True, only_if_empty=True, log_path=None):
    """The whole three-phase job. Returns (summary_text, result_dict)."""
    preflight(fc, where_clause, read_fields, write_fields, max_rows)
    work = read_worklist(fc, where_clause, read_fields, max_rows)
    if not work:
        return "No rows matched WHERE_CLAUSE. Nothing to do.", None
    decisions, failed = enrich(work, lookup)
    result = write_back(fc, where_clause, write_fields, decisions, dry_run, only_if_empty)
    if log_path:
        write_log(log_path, work, decisions, failed, result)
    return summarize(work, decisions, failed, result, max_rows), result


class Toolbox(object):
    def __init__(self):
        self.label = "Enrich From Service"
        self.alias = "enrichfromservice"
        self.tools = [EnrichFromService]


class EnrichFromService(object):
    def __init__(self):
        self.label = "Enrich From Service"
        self.description = (
            "Read a worklist, call an external service with no cursor open, write results back "
            "by OID. Dry run by default; a where clause is required."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        fc = arcpy.Parameter(displayName="Feature class", name="fc",
                             datatype="GPFeatureLayer", parameterType="Required", direction="Input")

        where = arcpy.Parameter(displayName="Where clause (rows that still need work)",
                                name="where", datatype="GPSQLExpression",
                                parameterType="Required", direction="Input")
        where.parameterDependencies = [fc.name]

        read = arcpy.Parameter(displayName="Read fields (OID@ is added automatically)",
                               name="read_fields", datatype="Field",
                               parameterType="Required", direction="Input", multiValue=True)
        read.parameterDependencies = [fc.name]

        write = arcpy.Parameter(displayName="Fields to write",
                                name="write_fields", datatype="Field",
                                parameterType="Required", direction="Input", multiValue=True)
        write.parameterDependencies = [fc.name]

        dry = arcpy.Parameter(displayName="Dry run (preview only, write nothing)",
                              name="dry_run", datatype="GPBoolean",
                              parameterType="Optional", direction="Input")
        dry.value = True

        cap = arcpy.Parameter(displayName="Maximum rows this run", name="max_rows",
                              datatype="GPLong", parameterType="Optional", direction="Input")
        cap.value = 500

        empty = arcpy.Parameter(displayName="Only fill values that are currently empty",
                                name="only_if_empty", datatype="GPBoolean",
                                parameterType="Optional", direction="Input")
        empty.value = True

        log = arcpy.Parameter(displayName="Write a JSON log (optional)", name="log",
                              datatype="DEFile", parameterType="Optional", direction="Output")
        log.filter.list = ["json"]

        return [fc, where, read, write, dry, cap, empty, log]

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):
        fc = parameters[0].valueAsText
        where = parameters[1].valueAsText
        read_fields = [OID] + [f for f in (parameters[2].valueAsText or "").split(";") if f]
        write_fields = [OID] + [f for f in (parameters[3].valueAsText or "").split(";") if f]
        dry_run = True if parameters[4].value is None else bool(parameters[4].value)
        max_rows = int(parameters[5].value) if parameters[5].value else 500
        only_if_empty = True if parameters[6].value is None else bool(parameters[6].value)
        log_path = parameters[7].valueAsText

        try:
            summary, result = run(fc, where, read_fields, write_fields, lookup,
                                  max_rows=max_rows, dry_run=dry_run,
                                  only_if_empty=only_if_empty, log_path=log_path)
        except ConfigError as exc:
            arcpy.AddError(str(exc))
            return

        for line in summary.splitlines():
            arcpy.AddMessage(line)

        if result and result["dry_run"] and result["changed"]:
            arcpy.AddWarning(
                "Dry run: {} row(s) WOULD change. Clear the Dry run box to apply.".format(
                    result["changed"]))
        elif result and not result["dry_run"] and result["changed"]:
            arcpy.AddMessage("{} row(s) updated.".format(result["changed"]))
