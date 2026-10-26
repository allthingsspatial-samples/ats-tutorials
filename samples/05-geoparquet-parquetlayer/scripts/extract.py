"""Cut a bounding box of Overture Maps places (release 2026-10-21.0) into a small GeoParquet file.

The Overture files are ZSTD-compressed; ParquetLayer reads only GZIP, Snappy or uncompressed files,
so the extract is written again with Snappy. Geometry: WKB points, GeoParquet 1.1 "geo" metadata.

Usage: python extract.py <name> <xmin> <ymin> <xmax> <ymax>
Needs: pip install duckdb pyarrow
"""
import json
import sys

import duckdb
import pyarrow.parquet as pq

RELEASE = "2026-10-21.0"
name, xmin, ymin, xmax, ymax = sys.argv[1], *map(float, sys.argv[2:6])

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
con.execute("SET s3_region = 'us-west-2'")

# Overture's bbox columns let DuckDB skip every row group outside the box.
table = con.execute(f"""
  SELECT id, names.primary AS name, basic_category AS category, operating_status AS status,
         confidence, addresses[1].locality AS city, addresses[1].region AS region,
         ST_AsWKB(geometry) AS geometry
  FROM read_parquet('s3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*.parquet')
  WHERE bbox.xmin BETWEEN {xmin} AND {xmax} AND bbox.ymin BETWEEN {ymin} AND {ymax}
  ORDER BY ST_Hilbert(geometry, ST_Extent(ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax})))
""").to_arrow_table()

geo = {"version": "1.1.0", "primary_column": "geometry",
       "columns": {"geometry": {"encoding": "WKB", "geometry_types": ["Point"]}}}
table = table.replace_schema_metadata({"geo": json.dumps(geo)})
pq.write_table(table, f"public/data/{name}-places.parquet", compression="snappy")
print(f"public/data/{name}-places.parquet: {table.num_rows:,} places")
