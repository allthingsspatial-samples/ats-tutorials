# con-04 mapclassify breaks (Python)

The Python side of CON-S01E04, on data classification. `main.py` reads the people per km² of the 254 Texas counties and prints the class breaks and the number of counties in each class for four methods from [mapclassify](https://pysal.org/mapclassify/):

- `FisherJenks`: natural breaks, the exact Fisher-Jenks optimum (least variance inside each class).
- `Quantiles`: the same number of counties in each class.
- `EqualInterval`: the same width for every class.
- `StdMean`: breaks at -2, -1, +1 and +2 standard deviations from the mean. On this skewed data the two classes below the mean fall under zero and stay empty, which is the point: standard deviation classes assume a roughly symmetric distribution.

What it teaches: one variable, one number of classes, four very different maps. With k = 5, equal interval puts 241 of 254 counties in the first class; quantile puts about 51 in each.

## Run

You need Python 3.13 (CI uses 3.13; other recent versions will likely work).

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py                   # k = 5
python main.py 7                 # any k from 3 to 7
```

`requirements.txt` pins mapclassify 2.11.0 and its dependencies, so the printed breaks stay the same. CI runs `python main.py` and compares the output with `expected-output.txt`, line by line.

## Data

`data/texas-county-density.csv` (254 rows: `GEOID`, `NAME`, `POP2024`, `LAND_KM2`, `DENSITY`) is built by `build_data.py` from two public US Census Bureau files (needs `pip install pyshp`, only to rebuild the data):

- Cartographic Boundary Files, counties 1:20,000,000, 2023 (county names and land area `ALAND`): https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_20m.zip
- Population Estimates Program, county totals, Vintage 2024 (July 1, 2024): https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv

`DENSITY` is `POP2024` divided by land area in km².

```bash
python build_data.py cb_2023_us_county_20m.shp co-est2024-alldata.csv data/texas-county-density.csv
```

The same data on a map, classified by the ArcGIS Maps SDK for JavaScript: [`samples/con-04-class-breaks`](../../samples/con-04-class-breaks/). Explore the concept interactively at https://concepts.allthingsspatial.io/concepts/classification/. All GIS Concepts episodes: https://www.youtube.com/playlist?list=PLHbasl_Mg-uE

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
