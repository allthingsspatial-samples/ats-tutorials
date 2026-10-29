"""Four ways to cut one variable into classes, with mapclassify.

Reads the 254 Texas counties in data/texas-county-density.csv and prints the class
breaks and class counts for Fisher-Jenks (natural breaks), Quantiles, Equal Interval
and Standard Deviation (StdMean). Same data, same number of classes, four different maps.

Usage: python main.py [k]   (k = number of classes, 3-7, default 5)
"""
import csv
import sys
import warnings
from pathlib import Path

# mapclassify falls back to pure Python without numba; the results are the same.
warnings.filterwarnings("ignore", message="Numba not installed")
import mapclassify  # noqa: E402

k = int(sys.argv[1]) if len(sys.argv) > 1 else 5
if not 3 <= k <= 7:
    sys.exit("k must be between 3 and 7")

with open(Path(__file__).parent / "data" / "texas-county-density.csv", encoding="utf-8", newline="") as f:
    density = [float(row["DENSITY"]) for row in csv.DictReader(f)]

print(f"Texas counties: {len(density)}, people per km2 (2024), k = {k}")
print(f"min {min(density):.2f}  max {max(density):.2f}  mean {sum(density) / len(density):.2f}")

classifiers = {
    # Natural breaks: minimise the variance inside each class (exact Fisher-Jenks, deterministic).
    "Fisher-Jenks": mapclassify.FisherJenks(density, k=k),
    # Same number of counties in each class (ties can make the counts uneven).
    "Quantiles": mapclassify.Quantiles(density, k=k),
    # Same width for every class: (max - min) / k.
    "EqualInterval": mapclassify.EqualInterval(density, k=k),
    # Breaks at -2, -1, +1 and +2 standard deviations from the mean. k does not apply here.
    # On skewed data like this, the classes below the mean fall under zero and stay empty.
    "StdMean": mapclassify.StdMean(density, multiples=[-2, -1, 1, 2]),
}

for name, classifier in classifiers.items():
    print()
    print(name)
    # Each class is lower < value <= upper; the first class has no lower bound.
    lower = "-inf"
    for upper, count in zip(classifier.bins, classifier.counts):
        print(f"  {lower:>9} - {upper:>9.2f}  {count:>4} counties")
        lower = f"{upper:.2f}"
