"""Feature querying and manipulation tools."""

import json

from ..qgis_env import require_qgis


def register_tools(mcp):
    """Register feature-related tools on the FastMCP instance."""

    @mcp.tool()
    def get_features(
        layer_id: str,
        limit: int = 100,
        offset: int = 0,
        attribute_filter: str | None = None,
        bbox: str | None = None,
        include_geometry: bool = True,
    ) -> str:
        """
        Query features from a vector layer.

        Args:
            layer_id: The layer ID to query.
            limit: Maximum number of features to return (default 100, max 1000).
            offset: Number of features to skip (for pagination).
            attribute_filter: Optional QGIS expression to filter features (e.g. "population > 1000").
            bbox: Optional bounding box as "xmin,ymin,xmax,ymax" to filter spatially.
            include_geometry: Whether to include geometry in GeoJSON format (default True).
        """
        require_qgis()
        from qgis.core import (
            QgsProject, QgsMapLayer, QgsFeatureRequest,
            QgsRectangle, QgsJsonExporter,
        )

        project = QgsProject.instance()
        layer = project.mapLayer(layer_id)
        if layer is None:
            return json.dumps({"error": f"Layer not found: {layer_id}"})
        if layer.type() != QgsMapLayer.VectorLayer:
            return json.dumps({"error": "Layer is not a vector layer"})

        limit = min(limit, 1000)

        request = QgsFeatureRequest()

        if attribute_filter:
            request.setFilterExpression(attribute_filter)

        if bbox:
            parts = bbox.split(",")
            if len(parts) == 4:
                rect = QgsRectangle(
                    float(parts[0]), float(parts[1]),
                    float(parts[2]), float(parts[3]),
                )
                request.setFilterRect(rect)

        request.setLimit(limit + offset)

        exporter = QgsJsonExporter()
        exporter.setIncludeGeometry(include_geometry)
        exporter.setIncludeAttributes(True)

        features = []
        count = 0
        for feat in layer.getFeatures(request):
            if count >= offset:
                features.append(exporter.exportFeature(feat))
            count += 1
            if len(features) >= limit:
                break

        return json.dumps({
            "layer_id": layer_id,
            "layer_name": layer.name(),
            "total_feature_count": layer.featureCount(),
            "returned": len(features),
            "offset": offset,
            "feature_collection": _parse_geojson_features(features),
        }, default=str)

    @mcp.tool()
    def get_feature_count(layer_id: str, attribute_filter: str | None = None) -> str:
        """
        Get the number of features in a vector layer, optionally filtered.

        Args:
            layer_id: The layer ID.
            attribute_filter: Optional QGIS expression to filter features.
        """
        require_qgis()
        from qgis.core import QgsProject, QgsMapLayer, QgsFeatureRequest

        project = QgsProject.instance()
        layer = project.mapLayer(layer_id)
        if layer is None:
            return json.dumps({"error": f"Layer not found: {layer_id}"})
        if layer.type() != QgsMapLayer.VectorLayer:
            return json.dumps({"error": "Layer is not a vector layer"})

        if attribute_filter:
            request = QgsFeatureRequest()
            request.setFilterExpression(attribute_filter)
            request.setNoAttributes()
            count = sum(1 for _ in layer.getFeatures(request))
        else:
            count = layer.featureCount()

        return json.dumps({
            "layer_id": layer_id,
            "layer_name": layer.name(),
            "feature_count": count,
        })

    @mcp.tool()
    def get_field_values(layer_id: str, field_name: str, distinct: bool = True, limit: int = 100) -> str:
        """
        Get unique or all values for a field in a vector layer.

        Args:
            layer_id: The layer ID.
            field_name: The field name to query.
            distinct: If True, return only unique values.
            limit: Maximum number of values to return.
        """
        require_qgis()
        from qgis.core import QgsProject, QgsMapLayer

        project = QgsProject.instance()
        layer = project.mapLayer(layer_id)
        if layer is None:
            return json.dumps({"error": f"Layer not found: {layer_id}"})
        if layer.type() != QgsMapLayer.VectorLayer:
            return json.dumps({"error": "Layer is not a vector layer"})

        field_idx = layer.fields().indexFromName(field_name)
        if field_idx < 0:
            field_names = [f.name() for f in layer.fields()]
            return json.dumps({
                "error": f"Field '{field_name}' not found",
                "available_fields": field_names,
            })

        limit = min(limit, 1000)
        values = []
        seen = set()

        for feat in layer.getFeatures():
            val = feat.attribute(field_idx)
            if val is not None:
                str_val = str(val)
                if distinct:
                    if str_val not in seen:
                        seen.add(str_val)
                        values.append(val)
                else:
                    values.append(val)
            if len(values) >= limit:
                break

        return json.dumps({
            "layer_id": layer_id,
            "field_name": field_name,
            "distinct": distinct,
            "value_count": len(values),
            "values": values,
        }, default=str)


def _parse_geojson_features(exported: list[str]) -> list[dict]:
    """Parse exported GeoJSON feature strings into a feature collection."""
    features = []
    for feat_str in exported:
        try:
            features.append(json.loads(feat_str))
        except json.JSONDecodeError:
            features.append({"error": "Could not parse feature", "raw": feat_str[:200]})
    return {"type": "FeatureCollection", "features": features}
