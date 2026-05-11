"""Raster analysis tools."""

import json
import tempfile
from pathlib import Path

from ..qgis_env import require_qgis


def register_tools(mcp):
    """Register raster analysis tools on the FastMCP instance."""

    @mcp.tool()
    def sample_raster(
        raster_layer_id: str,
        points: str,
    ) -> str:
        """
        Sample raster values at specified point coordinates.

        Args:
            raster_layer_id: The raster layer ID.
            points: JSON array of [x, y] coordinate pairs. E.g. '[[10.5, 52.3], [11.2, 52.8]]'.
        """
        require_qgis()
        from qgis.core import QgsProject, QgsMapLayer, QgsPointXY

        project = QgsProject.instance()
        layer = project.mapLayer(raster_layer_id)
        if layer is None:
            return json.dumps({"error": f"Layer not found: {raster_layer_id}"})
        if layer.type() != QgsMapLayer.RasterLayer:
            return json.dumps({"error": "Layer is not a raster layer"})

        try:
            coords = json.loads(points)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid points JSON: {e}"})

        provider = layer.dataProvider()
        results = []

        for coord in coords:
            if len(coord) < 2:
                continue
            point = QgsPointXY(float(coord[0]), float(coord[1]))
            sample = provider.sample(point, 1)
            if sample.valid:
                values = [sample.Value(i) for i in range(1, layer.bandCount() + 1)]
                results.append({
                    "x": coord[0], "y": coord[1],
                    "values": values,
                })
            else:
                results.append({
                    "x": coord[0], "y": coord[1],
                    "values": None,
                    "note": "No data at this location",
                })

        return json.dumps({
            "raster_layer": layer.name(),
            "band_count": layer.bandCount(),
            "samples": results,
        })

    @mcp.tool()
    def get_raster_statistics(raster_layer_id: str) -> str:
        """
        Get statistics for each band in a raster layer.

        Args:
            raster_layer_id: The raster layer ID.
        """
        require_qgis()
        from qgis.core import QgsProject, QgsMapLayer, QgsRasterBandStats

        project = QgsProject.instance()
        layer = project.mapLayer(raster_layer_id)
        if layer is None:
            return json.dumps({"error": f"Layer not found: {raster_layer_id}"})
        if layer.type() != QgsMapLayer.RasterLayer:
            return json.dumps({"error": "Layer is not a raster layer"})

        provider = layer.dataProvider()
        bands = []

        for band_num in range(1, layer.bandCount() + 1):
            stats = provider.bandStatistics(band_num, QgsRasterBandStats.All)
            bands.append({
                "band": band_num,
                "min": stats.minimumValue,
                "max": stats.maximumValue,
                "mean": stats.mean,
                "stddev": stats.stdDev,
                "sum": stats.sum,
                "range": stats.range,
            })

        return json.dumps({
            "raster": layer.name(),
            "width": layer.width(),
            "height": layer.height(),
            "bands": bands,
        })

    @mcp.tool()
    def clip_raster_by_extent(
        raster_layer_id: str,
        extent: str,
        output_file: str | None = None,
    ) -> str:
        """
        Clip a raster layer by a bounding box extent.

        Args:
            raster_layer_id: The raster layer ID.
            extent: Extent as "xmin,ymin,xmax,ymax".
            output_file: Optional output file path (.tif). If not provided, uses temp file.
        """
        require_qgis()
        from qgis.core import QgsProject, QgsMapLayer, QgsRectangle
        from qgis import processing

        project = QgsProject.instance()
        layer = project.mapLayer(raster_layer_id)
        if layer is None:
            return json.dumps({"error": f"Layer not found: {raster_layer_id}"})
        if layer.type() != QgsMapLayer.RasterLayer:
            return json.dumps({"error": "Layer is not a raster layer"})

        try:
            parts = [float(x) for x in extent.split(",")]
            rect = f"{parts[0]},{parts[1]},{parts[2]},{parts[3]}"
        except (ValueError, IndexError):
            return json.dumps({"error": "Invalid extent format. Use 'xmin,ymin,xmax,ymax'"})

        if output_file is None:
            output_file = str(Path(tempfile.gettempdir()) / "clipped_raster.tif")

        result = processing.run("gdal:cliprasterbyextent", {
            "INPUT": layer,
            "PROJWIN": rect,
            "OUTPUT": output_file,
        })

        return json.dumps({
            "output": str(result["OUTPUT"]),
            "extent": extent,
        })
