# -*- coding: utf-8 -*-
"""
Solar Screen All Counties - the script behind a script tool.

The stand-alone script from the last episode (solar_screen_all_counties.py),
changed in four places so ArcGIS Pro can run it as a geoprocessing tool:
  1. sys.argv + defaults     -> arcpy.GetParameterAsText(0..3)
  2. print()                 -> arcpy.AddMessage / AddWarning / AddError
  3. a silent loop           -> a step progressor (one step per county)
  4. the mosaic path         -> a derived output, arcpy.SetParameterAsText(4)
Environments come from the tool's Environments tab; the land cover is used
only when an environment is not set there.

Tool parameters (index = order in the tool's Parameters page):
  0 Counties workspace          Workspace        Input   Required
  1 Solar model inputs          Workspace        Input   Required
  2 Output workspace            Workspace        Input   Required
  3 Distance to lines (meters)  Double           Input   Optional (8000)
  4 Suitability mosaic          Raster Dataset   Output  Derived
"""
import os
import time

import arcpy
from arcpy.sa import (DistanceAccumulation, RescaleByFunction, Slope,
                      TfLinear, WeightedSum, WSTable)

# 1. Parameters from the tool dialog (zero-based, in dialog order)
counties_gdb = arcpy.GetParameterAsText(0)
inputs_gdb = arcpy.GetParameterAsText(1)
out_gdb = arcpy.GetParameterAsText(2)
max_distance = float(arcpy.GetParameterAsText(3) or 8000)

dem = os.path.join(inputs_gdb, "Elevation_3DEP_10m")
land_cover = os.path.join(inputs_gdb, "Land_Cover_NLCD_2025")
lines = os.path.join(inputs_gdb, "Transmission_Lines_HIFLD")
exclusions = os.path.join(inputs_gdb, "Exclusions_Wetlands_and_Protected_Areas")
W_SLOPE, W_LAND_COVER, W_DISTANCE = 0.164, 0.297, 0.539

arcpy.env.overwriteOutput = True          # the tool re-writes its own outputs
arcpy.CheckOutExtension("Spatial")


def solar_site_screen(county, name):
    """The Episode 9 Solar Site Screen model for one county. Returns the
    suitability raster path, or None when the county has no allowed area."""
    allowed = os.path.join(out_gdb, f"Allowed_area_{name}")
    arcpy.analysis.PairwiseErase(county, exclusions, allowed)
    if int(arcpy.management.GetCount(allowed)[0]) == 0:
        return None                            # no allowed area: skip

    slope_score = RescaleByFunction(Slope(dem, "DEGREE", 1, "PLANAR", "METER"),
                                    TfLinear(0, 10, "#", "#", 10, 1), 10, 1)
    distance = DistanceAccumulation(lines)
    with arcpy.EnvManager(mask=allowed):      # Mask: this one tool only
        distance_score = RescaleByFunction(
            distance, TfLinear(0, max_distance, "#", "#", max_distance, 1), 10, 1)
    suitability = WeightedSum(WSTable([[slope_score, "VALUE", W_SLOPE],
                                       [land_cover, "Solar_Score", W_LAND_COVER],
                                       [distance_score, "VALUE", W_DISTANCE]]))
    out = os.path.join(out_gdb, f"Suitability_{name}")
    suitability.save(out)
    return out


# Environments: the tool's Environments tab wins; the land cover fills the gaps
model_env = {k: land_cover for k in ("extent", "cellSize", "snapRaster")
             if not getattr(arcpy.env, k) or str(getattr(arcpy.env, k)) == "MAXOF"}

collected = []
with arcpy.EnvManager(**model_env):
    arcpy.env.workspace = counties_gdb
    counties = arcpy.ListFeatureClasses("*", "Polygon")
    if not counties:
        arcpy.AddError(f"No polygon feature classes in {counties_gdb}.")
        raise arcpy.ExecuteError

    # 3. A step progressor: one step per county
    arcpy.SetProgressor("step", "Screening counties...", 0, len(counties), 1)
    for n, name in enumerate(counties):
        arcpy.SetProgressorLabel(f"County {n + 1} of {len(counties)}: {name}")
        t0 = time.time()
        result = solar_site_screen(os.path.join(counties_gdb, name), name)
        if result:
            collected.append(result)
            arcpy.AddMessage(f"{n}  {name}: scored ({time.time() - t0:.0f} s)")
        else:
            arcpy.AddWarning(f"{n}  {name}: no allowed area, skipped")
        arcpy.SetProgressorPosition()
    arcpy.ResetProgressor()

if not collected:
    arcpy.AddError("No county has any allowed area. Nothing to mosaic.")
    raise arcpy.ExecuteError

mosaic = os.path.join(out_gdb, "Suitability_All_Counties")
first = arcpy.Describe(collected[0])            # cell size follows the county results
arcpy.management.MosaicToNewRaster(collected, out_gdb, "Suitability_All_Counties",
                                   first.spatialReference, "32_BIT_FLOAT",
                                   first.meanCellWidth, 1, "LAST", "FIRST")
arcpy.AddMessage(f"Mosaic of {len(collected)} counties: {mosaic}")

# 4. The derived output, so the result can be added to the map
arcpy.SetParameterAsText(4, mosaic)
