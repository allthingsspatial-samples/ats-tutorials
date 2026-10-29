"""Build public/data/colorado-counties.geojson from four public US government files.

Inputs (download them first, see the README):
  cb_2023_us_county_20m.shp      Census cartographic boundary counties 1:20,000,000 (2023)
  co-est2024-alldata.csv         Census Population Estimates, county totals, Vintage 2024
  2023-rural-urban-continuum-codes.csv   USDA ERS Rural-Urban Continuum Codes 2023
  climdiv-tmpccy-v1.0.0-<date>   NOAA NCEI nClimDiv county monthly mean temperature (deg F)

Usage: python build-data.py <county .shp> <pep .csv> <rucc .csv> <climdiv tmpccy file> <out.geojson>
Needs: pip install pyshp
"""
import csv
import json
import sys

import shapefile  # pyshp

STATE_FIPS = "08"   # Colorado in Census FIPS codes
CLIMDIV_STATE = "05"  # Colorado in the nClimDiv state numbering (alphabetical, not FIPS)
shp_path, pep_path, rucc_path, climdiv_path, out_path = sys.argv[1:6]

# Population, July 1 2024 estimate. SUMLEV 050 = county rows.
population = {}
with open(pep_path, encoding="latin-1", newline="") as f:
    for row in csv.DictReader(f):
        if row["SUMLEV"] == "050" and row["STATE"] == STATE_FIPS:
            population[row["STATE"] + row["COUNTY"]] = int(row["POPESTIMATE2024"])

# Rural-Urban Continuum Code 2023: 1-3 metro, 4-9 nonmetro. The file is long format.
rucc = {}
with open(rucc_path, encoding="latin-1", newline="") as f:
    for row in csv.DictReader(f):
        if row["FIPS"].startswith(STATE_FIPS) and row["Attribute"] == "RUCC_2023":
            rucc[row["FIPS"]] = int(row["Value"])

# Mean annual temperature 1991-2020. Each line: state(2) county(3) element(2) year(4), then 12 months.
annual = {}
with open(climdiv_path, encoding="ascii") as f:
    for line in f:
        parts = line.split()
        code, months = parts[0], [float(v) for v in parts[1:13]]
        state, county, year = code[0:2], code[2:5], int(code[7:11])
        if state != CLIMDIV_STATE or not 1991 <= year <= 2020 or min(months) < -99:
            continue
        annual.setdefault(STATE_FIPS + county, []).append(sum(months) / 12)
temperature = {fips: sum(v) / len(v) for fips, v in annual.items() if len(v) == 30}


def ring(points):
    # Shapefiles store outer rings clockwise; GeoJSON (RFC 7946) wants them counterclockwise,
    # so every ring is reversed (holes flip the other way too).
    return [[round(x, 5), round(y, 5)] for x, y in reversed(points)]


def signed_area(points):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(points, points[1:])) / 2


def geometry(shape):
    # One county can have more than one part (Arapahoe has an exclave), so group rings:
    # a clockwise ring starts a new polygon, a counterclockwise ring is a hole in the last one.
    starts = list(shape.parts) + [len(shape.points)]
    polygons = []
    for a, b in zip(starts[:-1], starts[1:]):
        points = shape.points[a:b]
        if signed_area(points) < 0 or not polygons:
            polygons.append([ring(points)])
        else:
            polygons[-1].append(ring(points))
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


features = []
reader = shapefile.Reader(shp_path)
for shape_rec in reader.iterShapeRecords():
    rec = shape_rec.record.as_dict()
    if rec["STATEFP"] != STATE_FIPS:
        continue
    fips = rec["GEOID"]
    land_km2 = rec["ALAND"] / 1e6
    code = rucc[fips]
    features.append({
        "type": "Feature",
        "properties": {
            "GEOID": fips,
            "NAME": rec["NAME"],
            "METRO": "Metro" if code <= 3 else "Nonmetro",
            "RUCC": code,
            "TEMP_F": round(temperature[fips], 1),
            "POP2024": population[fips],
            "LAND_KM2": round(land_km2, 1),
            "DENSITY": round(population[fips] / land_km2, 2),
        },
        "geometry": geometry(shape_rec.shape),
    })

features.sort(key=lambda feat: feat["properties"]["GEOID"])
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, separators=(",", ":"))
print(f"wrote {len(features)} counties to {out_path}")
