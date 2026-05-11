"""Resource registrations for the QGIS MCP server."""

import json

from ..qgis_env import require_qgis, is_qgis_available


def register_resources(mcp):
    """Register all resources on the FastMCP instance."""

    @mcp.resource("qgis://layers")
    def resource_layers() -> str:
        """Current layers in the QGIS project as JSON."""
        if not is_qgis_available():
            return json.dumps({"error": "QGIS not available", "layers": []})

        from qgis.core import QgsProject, QgsMapLayer

        project = QgsProject.instance()
        layers = []
        for layer in project.mapLayers().values():
            info = {
                "id": layer.id(),
                "name": layer.name(),
                "type": _layer_type_str(layer),
                "crs": layer.crs().authid() if layer.crs().isValid() else None,
            }
            if layer.type() == QgsMapLayer.VectorLayer:
                info["feature_count"] = layer.featureCount()
            layers.append(info)

        return json.dumps({"layer_count": len(layers), "layers": layers})

    @mcp.resource("qgis://layer/{layer_id}")
    def resource_layer_detail(layer_id: str) -> str:
        """Detailed information about a specific layer."""
        if not is_qgis_available():
            return json.dumps({"error": "QGIS not available"})

        from qgis.core import QgsProject, QgsMapLayer

        project = QgsProject.instance()
        layer = project.mapLayer(layer_id)
        if layer is None:
            return json.dumps({"error": f"Layer not found: {layer_id}"})

        info = {
            "id": layer.id(),
            "name": layer.name(),
            "type": _layer_type_str(layer),
            "crs": layer.crs().authid() if layer.crs().isValid() else None,
            "extent": _extent_dict(layer.extent()),
        }

        if layer.type() == QgsMapLayer.VectorLayer:
            info["feature_count"] = layer.featureCount()
            info["fields"] = [{"name": f.name(), "type": f.typeName()} for f in layer.fields()]

        return json.dumps(info)

    @mcp.resource("qgis://algorithms")
    def resource_algorithms() -> str:
        """Available QGIS processing algorithms."""
        if not is_qgis_available():
            return json.dumps({"error": "QGIS not available", "algorithms": []})

        from qgis.core import QgsApplication

        registry = QgsApplication.processingRegistry()
        algorithms = []
        for alg in registry.algorithms():
            algorithms.append({
                "id": alg.id(),
                "name": alg.displayName(),
                "provider": alg.provider().name() if alg.provider() else "unknown",
            })

        return json.dumps({"total": len(algorithms), "algorithms": algorithms})


def _layer_type_str(layer) -> str:
    from qgis.core import QgsMapLayer
    type_map = {
        QgsMapLayer.VectorLayer: "vector",
        QgsMapLayer.RasterLayer: "raster",
        QgsMapLayer.PluginLayer: "plugin",
        QgsMapLayer.MeshLayer: "mesh",
        QgsMapLayer.VectorTileLayer: "vector_tile",
        QgsMapLayer.PointCloudLayer: "point_cloud",
        QgsMapLayer.AnnotationLayer: "annotation",
        QgsMapLayer.GroupLayer: "group",
    }
    return type_map.get(layer.type(), f"unknown")


def _extent_dict(extent) -> dict:
    return {
        "xmin": extent.xMinimum(),
        "ymin": extent.yMinimum(),
        "xmax": extent.xMaximum(),
        "ymax": extent.yMaximum(),
    }
