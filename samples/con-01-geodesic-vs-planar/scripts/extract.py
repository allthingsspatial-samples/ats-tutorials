"""Cut Greenland and DR Congo out of the Natural Earth 1:50m countries GeoJSON.

Natural Earth is public domain (https://www.naturalearthdata.com/about/terms-of-use/).
Source file: ne_50m_admin_0_countries.geojson from
https://github.com/nvkelso/natural-earth-vector/tree/master/geojson

Usage: python extract.py <ne_50m_admin_0_countries.geojson> <out.geojson>
Needs: Python 3 only (standard library).
"""
import json
import sys

KEEP = {"GRL", "COD"}  # Greenland, Democratic Republic of the Congo

src, out = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as f:
    countries = json.load(f)


def rounded(coords):
    # 5 decimals is about 1 m: far finer than a 1:50m outline needs.
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 5), round(coords[1], 5)]
    return [rounded(c) for c in coords]


features = []
for feat in countries["features"]:
    props = feat["properties"]
    if props["ADM0_A3"] in KEEP:
        geom = feat["geometry"]
        features.append({
            "type": "Feature",
            "properties": {"name": props["NAME"], "iso3": props["ADM0_A3"]},
            "geometry": {"type": geom["type"], "coordinates": rounded(geom["coordinates"])},
        })

with open(out, "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, separators=(",", ":"))
print(f"wrote {len(features)} countries to {out}")
