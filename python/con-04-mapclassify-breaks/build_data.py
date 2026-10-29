"""Build data/texas-county-density.csv from two public US Census Bureau files.

Inputs (download them first, see the README):
  cb_2023_us_county_20m.dbf   Census cartographic boundary counties 1:20,000,000 (2023), attribute table
  co-est2024-alldata.csv      Census Population Estimates, county totals, Vintage 2024

Usage: python build_data.py <county .shp> <pep .csv> <out.csv>
Needs: pip install pyshp (only to rebuild the data; main.py does not need it)
"""
import csv
import sys

import shapefile  # pyshp

STATE_FIPS = "48"  # Texas in Census FIPS codes
shp_path, pep_path, out_path = sys.argv[1:4]

population = {}
with open(pep_path, encoding="latin-1", newline="") as f:
    for row in csv.DictReader(f):
        if row["SUMLEV"] == "050" and row["STATE"] == STATE_FIPS:
            population[row["STATE"] + row["COUNTY"]] = int(row["POPESTIMATE2024"])

rows = []
for rec in shapefile.Reader(shp_path).iterRecords():
    rec = rec.as_dict()
    if rec["STATEFP"] != STATE_FIPS:
        continue
    land_km2 = rec["ALAND"] / 1e6
    pop = population[rec["GEOID"]]
    rows.append([rec["GEOID"], rec["NAME"], pop, round(land_km2, 1), round(pop / land_km2, 2)])

rows.sort()
with open(out_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f, lineterminator="\n")
    writer.writerow(["GEOID", "NAME", "POP2024", "LAND_KM2", "DENSITY"])
    writer.writerows(rows)
print(f"wrote {len(rows)} counties to {out_path}")
