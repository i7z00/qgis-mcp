"""Project and layer management tools."""

import json
from pathlib import Path

from ..qgis_env import require_qgis


def register_tools(mcp):
    """Register project and layer management tools on the FastMCP instance."""

    @mcp.tool()
    def load_project(project_path: str) -> str:
        """
        Load a QGIS project file (.qgs or .qgz).

        Args:
            project_path: Absolute path to the QGIS project file.
        """
        require_qgis()
        from qgis.core import QgsProject, QgsMapLayer

        path = Path(project_path)
        if not path.exists():
            return json.dumps({"error": f"Project file not found: {project_path}"})

        project = QgsProject.instance()
        if not project.read(str(path)):
            return json.dumps({"error": f"Failed to load project: {project_path}"})

        layers = []
        for layer in project.mapLayers().values():
            layers.append({
                "id": layer.id(),
                "name": layer.name(),
                "type": _layer_type_str(layer),
                "crs": layer.crs().authid() if layer.crs().isValid() else None,
                "feature_count": layer.featureCount() if layer.type() == QgsMapLayer.VectorLayer else None,
            })

        return json.dumps({
            "project": str(path),
            "title": project.title() or path.stem,
            "crs": project.crs().authid() if project.crs().isValid() else None,
            "layer_count": len(layers),
            "layers": layers,
        })

    @mcp.tool()
    def load_vector_layer(file_path: str, layer_name: str | None = None) -> str:
        """
        Load a vector layer from a file (Shapefile, GeoJSON, GPKG, etc.).

        For GeoPackage files with multiple layers, use: 'path/to/file.gpkg|layername=layer_name'

        Args:
            file_path: Absolute path to the vector file. Use '|layername=X' for GeoPackage layers.
            layer_name: Optional display name for the layer.
        """
        require_qgis()
        from qgis.core import QgsVectorLayer

        actual_path, provider = _parse_layer_path(file_path)
        path = Path(actual_path)
        if not path.exists():
            return json.dumps({"error": f"File not found: {actual_path}"})

        name = layer_name or path.stem
        layer = QgsVectorLayer(file_path, name, provider)
        if not layer.isValid():
            return json.dumps({"error": f"Invalid vector layer: {file_path}"})

        from qgis.core import QgsProject
        QgsProject.instance().addMapLayer(layer)

        return json.dumps({
            "id": layer.id(),
            "name": layer.name(),
            "source": file_path,
            "geometry_type": _geometry_type_str(layer.geometryType()),
            "feature_count": layer.featureCount(),
            "crs": layer.crs().authid() if layer.crs().isValid() else None,
            "fields": [{"name": f.name(), "type": f.typeName()} for f in layer.fields()],
        })

    @mcp.tool()
    def load_raster_layer(file_path: str, layer_name: str | None = None) -> str:
        """
        Load a raster layer from a file (GeoTIFF, etc.).

        Args:
            file_path: Absolute path to the raster file.
            layer_name: Optional display name for the layer.
        """
        require_qgis()
        from qgis.core import QgsRasterLayer

        actual_path, _ = _parse_layer_path(file_path)
        path = Path(actual_path)
        if not path.exists():
            return json.dumps({"error": f"File not found: {actual_path}"})

        name = layer_name or path.stem
        layer = QgsRasterLayer(str(path), name)
        if not layer.isValid():
            return json.dumps({"error": f"Invalid raster layer: {file_path}"})

        from qgis.core import QgsProject
        QgsProject.instance().addMapLayer(layer)

        return json.dumps({
            "id": layer.id(),
            "name": layer.name(),
            "source": str(path),
            "width": layer.width(),
            "height": layer.height(),
            "band_count": layer.bandCount(),
            "crs": layer.crs().authid() if layer.crs().isValid() else None,
            "extent": _extent_to_dict(layer.extent()),
        })

    @mcp.tool()
    def list_layers() -> str:
        """
        List all layers currently loaded in the QGIS project.
        """
        require_qgis()
        from qgis.core import QgsProject, QgsMapLayer

        project = QgsProject.instance()
        layers = []
        for layer in project.mapLayers().values():
            info = {
                "id": layer.id(),
                "name": layer.name(),
                "type": _layer_type_str(layer),
                "crs": layer.crs().authid() if layer.crs().isValid() else None,
                "visible": project.layerTreeRoot().findLayer(layer.id()).isVisible() if project.layerTreeRoot().findLayer(layer.id()) else True,
            }
            if layer.type() == QgsMapLayer.VectorLayer:
                info["feature_count"] = layer.featureCount()
                info["geometry_type"] = _geometry_type_str(layer.geometryType())
            elif layer.type() == QgsMapLayer.RasterLayer:
                info["width"] = layer.width()
                info["height"] = layer.height()
                info["band_count"] = layer.bandCount()
            layers.append(info)

        return json.dumps({
            "layer_count": len(layers),
            "layers": layers,
        })

    @mcp.tool()
    def get_layer_info(layer_id: str) -> str:
        """
        Get detailed information about a specific layer.

        Args:
            layer_id: The ID of the layer (from list_layers).
        """
        require_qgis()
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
            "crs_description": layer.crs().description() if layer.crs().isValid() else None,
            "extent": _extent_to_dict(layer.extent()),
            "source": layer.source(),
        }

        if layer.type() == QgsMapLayer.VectorLayer:
            info["feature_count"] = layer.featureCount()
            info["geometry_type"] = _geometry_type_str(layer.geometryType())
            info["fields"] = [
                {
                    "name": f.name(),
                    "type": f.typeName(),
                    "length": f.length(),
                    "precision": f.precision(),
                }
                for f in layer.fields()
            ]
            info["wkb_type"] = layer.wkbType()

        elif layer.type() == QgsMapLayer.RasterLayer:
            info["width"] = layer.width()
            info["height"] = layer.height()
            info["band_count"] = layer.bandCount()
            info["data_type"] = str(layer.dataProvider().dataType(1)) if layer.bandCount() > 0 else None
            info["raster_units_per_pixel_x"] = layer.rasterUnitsPerPixelX()
            info["raster_units_per_pixel_y"] = layer.rasterUnitsPerPixelY()

        return json.dumps(info)

    @mcp.tool()
    def remove_layer(layer_id: str) -> str:
        """
        Remove a layer from the QGIS project.

        Args:
            layer_id: The ID of the layer to remove.
        """
        require_qgis()
        from qgis.core import QgsProject

        project = QgsProject.instance()
        layer = project.mapLayer(layer_id)
        if layer is None:
            return json.dumps({"error": f"Layer not found: {layer_id}"})

        name = layer.name()
        project.removeMapLayer(layer_id)
        return json.dumps({"removed": name, "id": layer_id})


def _layer_type_str(layer) -> str:
    """Get a human-readable layer type string."""
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
    return type_map.get(layer.type(), f"unknown_{layer.type()}")


def _geometry_type_str(geom_type: int) -> str:
    """Get a human-readable geometry type string."""
    from qgis.core import QgsWkbTypes
    type_map = {
        QgsWkbTypes.PointGeometry: "point",
        QgsWkbTypes.LineGeometry: "line",
        QgsWkbTypes.PolygonGeometry: "polygon",
        QgsWkbTypes.NullGeometry: "none",
        QgsWkbTypes.UnknownGeometry: "unknown",
    }
    return type_map.get(geom_type, "unknown")


def _extent_to_dict(extent) -> dict:
    """Convert QgsRectangle to a dictionary."""
    return {
        "xmin": extent.xMinimum(),
        "ymin": extent.yMinimum(),
        "xmax": extent.xMaximum(),
        "ymax": extent.yMaximum(),
    }


def _parse_layer_path(file_path: str) -> tuple[str, str]:
    """
    Parse a file path that may include QGIS provider-specific suffix.

    Handles formats like:
      - path/to/file.gpkg|layername=buildings → (path, "ogr")
      - path/to/file.shp → (path, "ogr")
      - path/to/file.tif → (path, "gdal")

    Returns (actual_file_path, provider_name).
    """
    if "|" in file_path:
        actual_path = file_path.split("|")[0]
    else:
        actual_path = file_path

    ext = Path(actual_path).suffix.lower()
    if ext in (".tif", ".tiff", ".geotiff"):
        provider = "gdal"
    else:
        provider = "ogr"

    return actual_path, provider
