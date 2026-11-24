# -*- coding: utf-8 -*-
# Reference copy of the on-camera MyTools.pyt (PRO-S03 A5): the Esri template's Toolbox class with label/alias/tools
# changed, and the Tool class replaced by ExportFeaturesToFolder (+ its export_features helper) from ATS-Starter.pyt.
import os
import time

import arcpy


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "My Tools"
        self.alias = "mytools"
        # List of tool classes associated with this toolbox
        self.tools = [ExportFeaturesToFolder]


EXPORT_FORMATS = ["GeoJSON", "Shapefile", "CSV", "File Geodatabase"]


class ExportFeaturesToFolder:
    """Exports a layer, or only the rows that match an SQL expression, to a
    folder as GeoJSON, a shapefile, a CSV table or a feature class in a file
    geodatabase. Episode A5 builds this tool line by line."""

    def __init__(self):
        self.label = "Export Features to Folder"
        self.description = ("Exports the features of a layer (all of them, or only those that "
                            "match an expression) to a folder as GeoJSON, a shapefile, a CSV "
                            "table or a feature class in a file geodatabase.")
        self.category = "Export"

    def getParameterInfo(self):
        in_features = arcpy.Parameter(
            displayName="Input Features", name="in_features",
            datatype="GPFeatureLayer", parameterType="Required", direction="Input")

        expression = arcpy.Parameter(
            displayName="Expression", name="where_clause",
            datatype="GPSQLExpression", parameterType="Optional", direction="Input")
        expression.parameterDependencies = [in_features.name]   # build it on the input fields

        out_folder = arcpy.Parameter(
            displayName="Output Folder", name="out_folder",
            datatype="DEFolder", parameterType="Required", direction="Input")

        out_format = arcpy.Parameter(
            displayName="Output Format", name="out_format",
            datatype="GPString", parameterType="Required", direction="Input")
        out_format.filter.type = "ValueList"
        out_format.filter.list = EXPORT_FORMATS
        out_format.value = "GeoJSON"

        out_name = arcpy.Parameter(
            displayName="Output Name", name="out_name",
            datatype="GPString", parameterType="Optional", direction="Input")

        out_path = arcpy.Parameter(
            displayName="Output", name="out_path",
            datatype="DEType", parameterType="Derived", direction="Output")

        return [in_features, expression, out_folder, out_format, out_name, out_path]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # Suggest an output name from the input the first time an input is chosen.
        in_features, out_name = parameters[0], parameters[4]
        if in_features.altered and in_features.value and not out_name.altered:
            out_name.value = arcpy.ValidateTableName(arcpy.Describe(in_features.value).baseName)
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        in_features = parameters[0].valueAsText
        where = parameters[1].valueAsText
        out_folder = parameters[2].valueAsText
        out_format = parameters[3].valueAsText
        out_name = parameters[4].valueAsText
        result = export_features(in_features, out_folder, out_format, where, out_name)
        parameters[5].value = result["output"]
        return

    def postExecute(self, parameters):
        return


def export_features(in_features, out_folder, out_format="GeoJSON", where=None, out_name=None):
    """Core logic, callable from Python and from the tool. Returns a dict with
    the output path, the number of features written and the seconds taken."""
    t0 = time.time()
    if out_format not in EXPORT_FORMATS:
        raise ValueError("Output Format must be one of %s" % ", ".join(EXPORT_FORMATS))
    base = out_name or arcpy.Describe(in_features).baseName
    base = arcpy.ValidateTableName(os.path.splitext(base)[0], out_folder)

    # One temporary layer holds only the matching rows, so every format exports the same subset.
    lyr = arcpy.management.MakeFeatureLayer(in_features, "ats_export_subset", where_clause=where)[0]
    try:
        count = int(arcpy.management.GetCount(lyr)[0])
        if count == 0:
            arcpy.AddWarning("The expression matches no features; the output will be empty.")
        arcpy.AddMessage("Exporting %d feature(s) as %s..." % (count, out_format))

        if out_format == "GeoJSON":
            out = os.path.join(out_folder, base + ".geojson")
            arcpy.conversion.FeaturesToJSON(lyr, out, geoJSON="GEOJSON", outputToWGS84="WGS84")
        elif out_format == "Shapefile":
            out = os.path.join(out_folder, base + ".shp")
            arcpy.conversion.ExportFeatures(lyr, out)
        elif out_format == "CSV":
            out = os.path.join(out_folder, base + ".csv")
            arcpy.conversion.ExportTable(lyr, out)
            arcpy.AddMessage("A CSV table holds the attributes only, not the shapes.")
        else:   # File Geodatabase
            gdb = os.path.join(out_folder, "Exports.gdb")
            if not arcpy.Exists(gdb):
                arcpy.management.CreateFileGDB(out_folder, "Exports.gdb")
            out = os.path.join(gdb, arcpy.ValidateTableName(base, gdb))
            arcpy.conversion.ExportFeatures(lyr, out)
    finally:
        arcpy.management.Delete(lyr)

    secs = round(time.time() - t0, 1)
    arcpy.AddMessage("Wrote %s (%d features, %.1f s)." % (out, count, secs))
    return dict(output=out, count=count, seconds=secs)
