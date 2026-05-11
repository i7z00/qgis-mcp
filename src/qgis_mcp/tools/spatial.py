"""Spatial analysis tools for geometry operations and spatial queries."""

import json
import tempfile
from pathlib import Path

from ..qgis_env import require_qgis


def register_tools(mcp):
    """Register spatial analysis tools on the FastMCP instance."""

    @mcp.tool()
    def get_extent(layer_ids: str | None = None) -> str:
        """
        Get the extent of specified layers or the full project extent.

        Args:
            layer_ids: Comma-separated list of layer IDs, or empty for full project extent.
        """
        require_qgis()
        from qgis.core import QgsProject, QgsRectangle

        project = QgsProject.instance()

        if layer_ids:
            ids = [lid.strip() for lid in layer_ids.split(",")]
            extents = {}
            for lid in ids:
                layer = project.mapLayer(lid)
                if layer:
                    ext = layer.extent()
                    extents[lid] = {
                        "name": layer.name(),
                        "extent": _extent_to_dict(ext),
                        "width": ext.width(),
                        "height": ext.height(),
                        "center": {"x": ext.center().x(), "y": ext.center().y()},
                    }
                else:
                    extents[lid] = {"error": "Layer not found"}
            return json.dumps({"layers": extents})

        # Full project extent
        all_layers = list(project.mapLayers().values())
        if not all_layers:
            return json.dumps({"error": "No layers loaded"})

        full_extent = QgsRectangle()
        first = True
        for layer in all_layers:
            if first:
                full_extent = layer.extent()
                first = False
            else:
                full_extent.combineExtentWith(layer.extent())

        return json.dumps({
            "extent": _extent_to_dict(full_extent),
            "width": full_extent.width(),
            "height": full_extent.height(),
            "center": {"x": full_extent.center().x(), "y": full_extent.center().y()},
        })

    @mcp.tool()
    def buffer(
        input_layer_id: str,
        distance: float,
        output_file: str | None = None,
        dissolve: bool = False,
        segments: int = 5,
    ) -> str:
        """
        Create a buffer around features in a vector layer.

        Args:
            input_layer_id: The layer ID to buffer.
            distance: Buffer distance in layer units.
            output_file: Optional output file path (GeoJSON, GPKG, etc.). If not provided, returns GeoJSON.
            dissolve: Whether to dissolve overlapping buffers.
            segments: Number of segments for rounded buffers.
        """
        require_qgis()
        from qgis.core import (
            QgsProject, QgsMapLayer, QgsVectorFileWriter,
            QgsCoordinateReferenceSystem, QgsCoordinateTransformContext,
            QgsJsonExporter,
        )
        from qgis import processing

        project = QgsProject.instance()
        layer = project.mapLayer(input_layer_id)
        if layer is None:
            return json.dumps({"error": f"Layer not found: {input_layer_id}"})
        if layer.type() != QgsMapLayer.VectorLayer:
            return json.dumps({"error": "Layer is not a vector layer"})

        params = {
            "INPUT": layer,
            "DISTANCE": distance,
            "SEGMENTS": segments,
            "DISSOLVE": dissolve,
        }

        if output_file:
            params["OUTPUT"] = output_file
            result = processing.run("native:buffer", params)
            output_path = result["OUTPUT"]
            return json.dumps({
                "output": str(output_path),
                "algorithm": "native:buffer",
                "distance": distance,
                "dissolve": dissolve,
            })
        else:
            # Use temporary output and return GeoJSON
            with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                params["OUTPUT"] = tmp_path
                result = processing.run("native:buffer", params)

                buffered_layer = result["OUTPUT"]
                if isinstance(buffered_layer, str):
                    buffered_layer = _load_temp_layer(buffered_layer)

                if buffered_layer:
                    features = []
                    exporter = QgsJsonExporter()
                    for feat in buffered_layer.getFeatures():
                        features.append(json.loads(exporter.exportFeature(feat)))

                    return json.dumps({
                        "feature_collection": {
                            "type": "FeatureCollection",
                            "features": features,
                        },
                        "feature_count": len(features),
                        "distance": distance,
                        "dissolve": dissolve,
                    }, default=str)
                else:
                    return json.dumps({"error": "Buffer operation produced no output"})
            finally:
                try:
                    _safe_unlink
                except Exception:
                    pass

    @mcp.tool()
    def spatial_query(
        source_layer_id: str,
        reference_layer_id: str,
        predicate: str = "intersects",
    ) -> str:
        """
        Select features from a source layer based on spatial relationship with a reference layer.

        Args:
            source_layer_id: The layer to select features FROM.
            reference_layer_id: The layer to use for spatial filtering.
            predicate: Spatial predicate: 'intersects', 'contains', 'within', 'crosses', 'touches', 'disjoint', 'equals'.
        """
        require_qgis()
        from qgis.core import QgsProject, QgsMapLayer, QgsJsonExporter
        from qgis import processing

        project = QgsProject.instance()
        source = project.mapLayer(source_layer_id)
        ref = project.mapLayer(reference_layer_id)

        if not source:
            return json.dumps({"error": f"Source layer not found: {source_layer_id}"})
        if not ref:
            return json.dumps({"error": f"Reference layer not found: {reference_layer_id}"})

        valid_predicates = {
            "intersects": 0, "contains": 1, "disjoint": 2,
            "equals": 3, "touches": 4, "overlaps": 5,
            "within": 6, "crosses": 7,
        }

        if predicate.lower() not in valid_predicates:
            return json.dumps({
                "error": f"Invalid predicate: {predicate}",
                "valid_predicates": list(valid_predicates.keys()),
            })

        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = processing.run("native:extractbylocation", {
                "INPUT": source,
                "PREDICATE": [valid_predicates[predicate.lower()]],
                "INTERSECT": ref,
                "OUTPUT": tmp_path,
            })

            output_layer = _load_temp_layer(tmp_path)
            if output_layer:
                features = []
                exporter = QgsJsonExporter()
                for feat in output_layer.getFeatures():
                    features.append(json.loads(exporter.exportFeature(feat)))

                return json.dumps({
                    "source_layer": source.name(),
                    "reference_layer": ref.name(),
                    "predicate": predicate.lower(),
                    "source_feature_count": source.featureCount(),
                    "selected_count": len(features),
                    "feature_collection": {
                        "type": "FeatureCollection",
                        "features": features,
                    },
                }, default=str)
            else:
                return json.dumps({"error": "Spatial query produced no output"})
        finally:
            _safe_unlink

    @mcp.tool()
    def reproject_layer(
        layer_id: str,
        target_crs: str,
        output_file: str | None = None,
    ) -> str:
        """
        Reproject a layer to a different coordinate reference system.

        Args:
            layer_id: The layer ID to reproject.
            target_crs: Target CRS (e.g. 'EPSG:4326', 'EPSG:3857').
            output_file: Optional output file path. If not provided, returns GeoJSON.
        """
        require_qgis()
        from qgis.core import QgsProject, QgsMapLayer, QgsJsonExporter, QgsCoordinateReferenceSystem
        from qgis import processing

        project = QgsProject.instance()
        layer = project.mapLayer(layer_id)
        if not layer:
            return json.dumps({"error": f"Layer not found: {layer_id}"})

        target = QgsCoordinateReferenceSystem(target_crs)
        if not target.isValid():
            return json.dumps({"error": f"Invalid target CRS: {target_crs}"})

        if output_file:
            result = processing.run("native:reprojectlayer", {
                "INPUT": layer,
                "TARGET_CRS": target,
                "OUTPUT": output_file,
            })
            return json.dumps({
                "output": str(result["OUTPUT"]),
                "source_crs": layer.crs().authid() or "unknown",
                "target_crs": target_crs,
            })

        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = processing.run("native:reprojectlayer", {
                "INPUT": layer,
                "TARGET_CRS": target,
                "OUTPUT": tmp_path,
            })

            out_layer = result["OUTPUT"]
            if isinstance(out_layer, str):
                out_layer = _load_temp_layer(out_layer)

            features = []
            if out_layer:
                exporter = QgsJsonExporter()
                for feat in out_layer.getFeatures():
                    features.append(json.loads(exporter.exportFeature(feat)))

            return json.dumps({
                "source_crs": layer.crs().authid() or "unknown",
                "target_crs": target_crs,
                "feature_count": len(features),
                "feature_collection": {
                    "type": "FeatureCollection",
                    "features": features,
                },
            }, default=str)
        finally:
            _safe_unlink

    @mcp.tool()
    def get_crs_info(crs_authid: str | None = None) -> str:
        """
        Get information about a coordinate reference system.

        Args:
            crs_authid: CRS authority ID (e.g. 'EPSG:4326'). If None, returns info for current project CRS.
        """
        require_qgis()
        from qgis.core import QgsCoordinateReferenceSystem, QgsProject

        if crs_authid is None:
            crs = QgsProject.instance().crs()
        else:
            crs = QgsCoordinateReferenceSystem(crs_authid)

        if not crs.isValid():
            return json.dumps({"error": f"Invalid CRS: {crs_authid or 'project CRS'}"})

        return json.dumps({
            "authid": crs.authid(),
            "description": crs.description(),
            "is_geographic": crs.isGeographic(),
            "wkt": crs.toWkt(),
            "proj4": crs.toProj(),
            "units": str(crs.mapUnits()),
        })

    @mcp.tool()
    def calculate_field(
        layer_id: str,
        field_name: str,
        expression: str,
        field_type: str = "double",
    ) -> str:
        """
        Add or calculate a field in a vector layer using a QGIS expression.

        Args:
            layer_id: The layer ID.
            field_name: Name of the field to create or update.
            expression: QGIS expression to evaluate (e.g. '$area', 'population / area').
            field_type: Field data type: 'double', 'int', 'string'.
        """
        require_qgis()
        from qgis.core import (
            QgsProject, QgsMapLayer, QgsField, QgsExpression,
            QgsExpressionContext, QgsExpressionContextUtils,
        )
        from qgis.PyQt.QtCore import QVariant

        project = QgsProject.instance()
        layer = project.mapLayer(layer_id)
        if not layer:
            return json.dumps({"error": f"Layer not found: {layer_id}"})
        if layer.type() != QgsMapLayer.VectorLayer:
            return json.dumps({"error": "Layer is not a vector layer"})

        type_map = {
            "double": QVariant.Double,
            "int": QVariant.Int,
            "string": QVariant.String,
        }
        variant_type = type_map.get(field_type, QVariant.Double)

        # Add field if it doesn't exist
        if layer.fields().indexFromName(field_name) < 0:
            provider = layer.dataProvider()
            provider.addAttributes([QgsField(field_name, variant_type)])
            layer.updateFields()

        expr = QgsExpression(expression)
        if expr.hasParserError():
            return json.dumps({"error": f"Expression parse error: {expr.parserErrorString()}"})

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.layerScope(layer))

        layer.startEditing()
        field_idx = layer.fields().indexFromName(field_name)
        updated = 0

        for feat in layer.getFeatures():
            context.setFeature(feat)
            value = expr.evaluate(context)
            if expr.hasEvalError():
                continue
            layer.changeAttributeValue(feat.id(), field_idx, value)
            updated += 1

        layer.commitChanges()

        return json.dumps({
            "layer_id": layer_id,
            "field_name": field_name,
            "expression": expression,
            "features_updated": updated,
        })

    @mcp.tool()
    def calculate_area_length(layer_id: str) -> str:
        """
        Compute area (for polygons) and length/perimeter (for lines/polygons)
        and return statistics.

        Args:
            layer_id: The layer ID to analyze.
        """
        require_qgis()
        from qgis.core import QgsProject, QgsMapLayer, QgsDistanceArea, QgsWkbTypes

        project = QgsProject.instance()
        layer = project.mapLayer(layer_id)
        if not layer:
            return json.dumps({"error": f"Layer not found: {layer_id}"})
        if layer.type() != QgsMapLayer.VectorLayer:
            return json.dumps({"error": "Layer is not a vector layer"})

        da = QgsDistanceArea()
        da.setSourceCrs(layer.crs(), QgsProject.instance().transformContext())
        da.setEllipsoid(layer.crs().ellipsoidAcronym())

        geom_type = layer.geometryType()
        areas = []
        lengths = []

        for feat in layer.getFeatures():
            geom = feat.geometry()
            if not geom:
                continue
            if geom_type == QgsWkbTypes.PolygonGeometry:
                areas.append(da.measureArea(geom))
                lengths.append(da.measurePerimeter(geom))
            elif geom_type == QgsWkbTypes.LineGeometry:
                lengths.append(da.measureLength(geom))
            elif geom_type == QgsWkbTypes.PointGeometry:
                pass  # Points have no area or length

        result = {"layer_id": layer_id, "layer_name": layer.name(), "units": str(da.lengthUnits())}

        if areas:
            result["area"] = {
                "min": min(areas), "max": max(areas),
                "sum": sum(areas), "mean": sum(areas) / len(areas),
            }
        if lengths:
            result["length"] = {
                "min": min(lengths), "max": max(lengths),
                "sum": sum(lengths), "mean": sum(lengths) / len(lengths),
            }

        return json.dumps(result)


def _extent_to_dict(extent) -> dict:
    return {
        "xmin": extent.xMinimum(),
        "ymin": extent.yMinimum(),
        "xmax": extent.xMaximum(),
        "ymax": extent.yMaximum(),
    }


def _safe_unlink(path: str) -> None:
    """Safely try to delete a temp file, ignoring Windows file lock errors."""
    try:
        Path(path).unlink(missing_ok=True)
    except PermissionError:
        pass  # File still locked by QGIS, will be cleaned up on exit


def _load_temp_layer(path: str):
    """Load a temporary vector layer from a file path."""
    from qgis.core import QgsVectorLayer
    layer = QgsVectorLayer(path, "temp", "ogr")
    return layer if layer.isValid() else None
