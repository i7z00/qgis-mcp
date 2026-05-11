"""Project and layer management tools."""

import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from ..qgis_env import require_qgis


def _inject_mapcanvas(project_path: str, project) -> bool:
    """
    Post-process a .qgs file to inject <mapcanvas> if missing.

    Returns True if injection happened, False if already present or failed.
    """
    try:
        tree = ET.parse(project_path)
        root = tree.getroot()

        if root.find("mapcanvas") is not None:
            return False

        from qgis.core import QgsCoordinateTransform

        project_crs = project.crs()
        layers = list(project.mapLayers().values())
        if layers:
            xmin = ymin = xmax = ymax = None
            for layer in layers:
                ext = layer.extent()
                layer_crs = layer.crs()
                if layer_crs.isValid() and project_crs.isValid() and layer_crs != project_crs:
                    transform = QgsCoordinateTransform(layer_crs, project_crs, project)
                    ext = transform.transformBoundingBox(ext)
                if xmin is None:
                    xmin, ymin, xmax, ymax = ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum()
                else:
                    xmin = min(xmin, ext.xMinimum())
                    ymin = min(ymin, ext.yMinimum())
                    xmax = max(xmax, ext.xMaximum())
                    ymax = max(ymax, ext.yMaximum())
        else:
            xmin = ymin = xmax = ymax = 0.0

        insert_idx = 0
        for i, child in enumerate(root):
            if child.tag == "projectCrs":
                insert_idx = i + 1
                break

        mc = ET.Element("mapcanvas", {"annotationsVisible": "1", "name": "theMapCanvas"})
        ET.SubElement(mc, "units").text = "meters"
        extent_el = ET.SubElement(mc, "extent")
        ET.SubElement(extent_el, "xmin").text = str(xmin)
        ET.SubElement(extent_el, "ymin").text = str(ymin)
        ET.SubElement(extent_el, "xmax").text = str(xmax)
        ET.SubElement(extent_el, "ymax").text = str(ymax)
        ET.SubElement(mc, "rotation").text = "0"

        dest_srs = ET.SubElement(mc, "destinationsrs")
        project_crs_el = root.find("projectCrs/spatialrefsys")
        if project_crs_el is not None:
            dest_srs.append(copy.deepcopy(project_crs_el))
        else:
            ET.SubElement(dest_srs, "spatialrefsys")

        ET.SubElement(mc, "rendermaptile").text = "0"
        ET.SubElement(mc, "expressionContextScope")

        root.insert(insert_idx, mc)
        tree.write(project_path, encoding="UTF-8", xml_declaration=True)
        return True
    except Exception:
        return False


def save_project_file(project, project_path: str, make_paths_absolute: bool = False) -> dict:
    """
    Save a QGIS project with headless→Desktop compatibility fixes.

    This is the standalone implementation used by both the MCP tool and
    direct scripts. It saves the project and injects <mapcanvas> if missing.
    """
    from qgis.core import QgsProject

    path = Path(project_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if make_paths_absolute:
        project.setFilePathStorage(QgsProject.Absolute)
    else:
        project.setFilePathStorage(QgsProject.Relative)

    ok = project.write(str(path))
    if not ok:
        return {"ok": False, "error": f"Failed to write project: {project_path}"}

    injected = _inject_mapcanvas(str(path), project)
    return {
        "ok": True,
        "project": str(path),
        "layer_count": len(project.mapLayers()),
        "crs": project.crs().authid() if project.crs().isValid() else None,
        "canvas_injected": injected,
    }


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
    def validate_project() -> str:
        """
        Validate the current QGIS project for common issues.

        Checks:
        - Project CRS is valid
        - All layers have valid datasources (files exist)
        - All layers have valid CRS
        - Layer extents are non-empty
        - If saving to Desktop, warns if <mapcanvas> would be missing
        """
        require_qgis()
        from qgis.core import QgsProject, QgsMapLayer

        project = QgsProject.instance()
        issues = []
        warnings = []

        # 1. Project CRS
        if not project.crs().isValid():
            issues.append("Project CRS is invalid or not set.")
        else:
            if project.crs().isGeographic():
                warnings.append(f"Project CRS is geographic ({project.crs().authid()}). Consider a projected CRS for analysis.")

        # 2. Layer checks
        layers = list(project.mapLayers().values())
        if not layers:
            issues.append("Project has no layers.")

        for layer in layers:
            # Datasource validity
            if not layer.isValid():
                issues.append(f"Layer '{layer.name()}' is invalid.")
                continue

            # File existence for file-based layers
            src = layer.source()
            if "|" in src:
                src = src.split("|")[0]
            if src and not src.lower().startswith("http"):
                p = Path(src)
                if not p.exists():
                    issues.append(f"Layer '{layer.name()}' source not found: {src}")

            # CRS validity
            if not layer.crs().isValid():
                issues.append(f"Layer '{layer.name()}' has invalid CRS.")

            # Extent non-empty
            ext = layer.extent()
            if ext.isEmpty() or ext.isNull():
                warnings.append(f"Layer '{layer.name()}' has empty extent.")

        # 3. Headless warning
        warnings.append("Running headless — use 'save_project' tool (not raw write) to ensure Desktop compatibility.")

        status = "ok" if not issues else "failed"
        return json.dumps({
            "status": status,
            "layer_count": len(layers),
            "project_crs": project.crs().authid() if project.crs().isValid() else None,
            "issues": issues,
            "warnings": warnings,
        })

    @mcp.tool()
    def save_project(project_path: str, make_paths_absolute: bool = False) -> str:
        """
        Save the current QGIS project to a file.

        This tool fixes the common headless→Desktop issue by injecting a
        <mapcanvas> element if QGIS omitted it (which happens when running
        without a GUI). The canvas extent is computed from the combined
        bounding box of all layers.

        Args:
            project_path: Absolute path where the .qgs file should be saved.
            make_paths_absolute: If True, convert all layer paths to absolute
                before saving. Recommended when the project file will be moved.
        """
        require_qgis()
        from qgis.core import QgsProject

        project = QgsProject.instance()
        result = save_project_file(project, project_path, make_paths_absolute)
        if not result["ok"]:
            return json.dumps({"error": result["error"]})
        return json.dumps(result)

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
