"""Build public/data/texas-counties.geojson from two public US Census Bureau files.

Inputs (download them first, see the README):
  cb_2023_us_county_20m.shp   Census cartographic boundary counties 1:20,000,000 (2023)
  co-est2024-alldata.csv      Census Population Estimates, county totals, Vintage 2024

Usage: python build-data.py <county .shp> <pep .csv> <out.geojson>
Needs: pip install pyshp
"""
import csv
import json
import sys

import shapefile  # pyshp

STATE_FIPS = "48"  # Texas in Census FIPS codes
shp_path, pep_path, out_path = sys.argv[1:4]

# Population, July 1 2024 estimate. SUMLEV 050 = county rows.
population = {}
with open(pep_path, encoding="latin-1", newline="") as f:
    for row in csv.DictReader(f):
        if row["SUMLEV"] == "050" and row["STATE"] == STATE_FIPS:
            population[row["STATE"] + row["COUNTY"]] = int(row["POPESTIMATE2024"])


def ring(points):
    # Shapefiles store outer rings clockwise; GeoJSON (RFC 7946) wants them counterclockwise,
    # so every ring is reversed (holes flip the other way too).
    return [[round(x, 4), round(y, 4)] for x, y in reversed(points)]


def signed_area(points):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(points, points[1:])) / 2


def geometry(shape):
    # A county can have more than one part (coastal islands), so group rings:
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
    features.append({
        "type": "Feature",
        "properties": {
            "GEOID": fips,
            "NAME": rec["NAME"],
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
