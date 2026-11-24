# -*- coding: utf-8 -*-
"""
Solar Screen All Counties - a stand-alone Python script.

Started as the ModelBuilder export (Export > Export To Python File) of the
PRO-S03 A2 model, then cleaned up:
  1. Iterate Feature Classes  -> a for loop over arcpy.ListFeatureClasses()
  2. If Row Count Is + precondition -> an if block on Get Count
  3. Collect Values           -> a Python list
  4. hard-coded paths         -> paths relative to this file (or arguments)
  5. overwriteOutput          -> True, so the script can run again

Run it with the ArcGIS Pro Python, with ArcGIS Pro closed or open:
    propy.bat solar_screen_all_counties.py [counties_gdb] [inputs_gdb] [out_gdb]
"""
import os
import sys
import time

import arcpy
from arcpy.sa import (DistanceAccumulation, RescaleByFunction, Slope,
                      TfLinear, WeightedSum, WSTable)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

# Inputs (arguments win over the defaults next to this script)
args = sys.argv[1:] + [None] * 3
counties_gdb = args[0] or os.path.join(DATA, "Counties.gdb")
inputs_gdb = args[1] or os.path.join(DATA, "Solar_Model_Inputs.gdb")
out_gdb = os.path.abspath(args[2] or os.path.join(HERE, "..", "reference", "A3_reference.gdb"))

dem = os.path.join(inputs_gdb, "Elevation_3DEP_10m")
land_cover = os.path.join(inputs_gdb, "Land_Cover_NLCD_2025")
lines = os.path.join(inputs_gdb, "Transmission_Lines_HIFLD")
exclusions = os.path.join(inputs_gdb, "Exclusions_Wetlands_and_Protected_Areas")
W_SLOPE, W_LAND_COVER, W_DISTANCE = 0.164, 0.297, 0.539

arcpy.env.overwriteOutput = True          # the export sets this to False
arcpy.CheckOutExtension("Spatial")
if not arcpy.Exists(out_gdb):
    arcpy.management.CreateFileGDB(*os.path.split(out_gdb))


def solar_site_screen(county, name):
    """The Episode 9 Solar Site Screen model for one county. Returns the
    suitability raster path, or None when the county has no allowed area."""
    allowed = os.path.join(out_gdb, f"Allowed_area_{name}")
    arcpy.analysis.PairwiseErase(county, exclusions, allowed)

    # If Row Count Is (Is Greater Than 0) + precondition -> an if block
    if int(arcpy.management.GetCount(allowed)[0]) == 0:
        return None                            # no allowed area: skip

    slope_score = RescaleByFunction(Slope(dem, "DEGREE", 1, "PLANAR", "METER"),
                                    TfLinear(0, 10, "#", "#", 10, 1), 10, 1)
    distance = DistanceAccumulation(lines)
    with arcpy.EnvManager(mask=allowed):      # a tool-level environment
        distance_score = RescaleByFunction(distance, TfLinear(0, 8000, "#", "#", 8000, 1), 10, 1)
    suitability = WeightedSum(WSTable([[slope_score, "VALUE", W_SLOPE],
                                       [land_cover, "Solar_Score", W_LAND_COVER],
                                       [distance_score, "VALUE", W_DISTANCE]]))
    out = os.path.join(out_gdb, f"Suitability_{name}")
    suitability.save(out)
    return out


# Model environments: extent, cell size and snap raster = the land cover
collected = []                                 # Collect Values -> a list
with arcpy.EnvManager(extent=land_cover, cellSize=land_cover, snapRaster=land_cover):
    arcpy.env.workspace = counties_gdb
    # Iterate Feature Classes -> a for loop (%n% = n, %Name% = name)
    for n, name in enumerate(arcpy.ListFeatureClasses("*", "Polygon")):
        t0 = time.time()
        result = solar_site_screen(os.path.join(counties_gdb, name), name)
        if result:
            collected.append(result)
        print(f"{n}  {name}: {'scored' if result else 'skipped'} "
                         f"({time.time() - t0:.0f} s)")

# Runs once, after the loop (the main model)
arcpy.management.MosaicToNewRaster(collected, out_gdb, "Suitability_All_Counties",
                                   arcpy.Describe(collected[0]).spatialReference,
                                   "32_BIT_FLOAT", 30, 1, "LAST", "FIRST")
print(f"Mosaic of {len(collected)} counties: "
                 f"{os.path.join(out_gdb, 'Suitability_All_Counties')}")
