"""Map export and rendering tools."""

import json
import tempfile
from pathlib import Path

from ..qgis_env import require_qgis


def register_tools(mcp):
    """Register map export tools on the FastMCP instance."""

    @mcp.tool()
    def export_map_image(
        output_path: str | None = None,
        width: int = 800,
        height: int = 600,
        extent: str | None = None,
        layers: str | None = None,
        dpi: int = 96,
    ) -> str:
        """
        Export the current map view as an image file (PNG).

        Args:
            output_path: File path for the output image. If None, saves to a temp file.
            width: Image width in pixels (default 800).
            height: Image height in pixels (default 600).
            extent: Extent as "xmin,ymin,xmax,ymax". If None, uses project extent.
            layers: Comma-separated layer IDs to render. If None, renders all visible.
            dpi: DPI for rendering (default 96).
        """
        require_qgis()
        from qgis.core import (
            QgsProject, QgsMapSettings, QgsRectangle,
            QgsMapRendererCustomPainterJob,
        )
        from qgis.PyQt.QtGui import QImage, QPainter

        project = QgsProject.instance()

        # Determine extent
        if extent:
            try:
                parts = [float(x) for x in extent.split(",")]
                map_extent = QgsRectangle(parts[0], parts[1], parts[2], parts[3])
            except (ValueError, IndexError):
                return json.dumps({"error": "Invalid extent format. Use 'xmin,ymin,xmax,ymax'"})
        else:
            map_extent = QgsRectangle()
            first = True
            for layer in project.mapLayers().values():
                if first:
                    map_extent = layer.extent()
                    first = False
                else:
                    map_extent.combineExtentWith(layer.extent())
            if first:
                return json.dumps({"error": "No layers loaded to determine extent"})

        # Configure map settings
        settings = QgsMapSettings()
        settings.setExtent(map_extent)
        settings.setOutputSize(QgsMapSettings.Size(width, height))
        settings.setOutputDpi(dpi)

        # Set layers to render
        if layers:
            layer_ids = [lid.strip() for lid in layers.split(",")]
            render_layers = [project.mapLayer(lid) for lid in layer_ids if project.mapLayer(lid)]
        else:
            root = project.layerTreeRoot()
            render_layers = [node.layer() for node in root.findLayers() if node.isVisible()]

        if not render_layers:
            return json.dumps({"error": "No layers to render"})

        settings.setLayers(render_layers)

        # Render to image
        image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        image.fill(0xFFFFFFFF)  # White background

        painter = QPainter(image)
        renderer = QgsMapRendererCustomPainterJob(settings, painter)
        renderer.start()
        renderer.waitForFinished()
        painter.end()

        # Save
        save_path = output_path or str(Path(tempfile.gettempdir()) / "qgis_map_export.png")
        image.save(save_path)

        return json.dumps({
            "output": save_path,
            "width": width,
            "height": height,
            "dpi": dpi,
            "extent": {
                "xmin": map_extent.xMinimum(),
                "ymin": map_extent.yMinimum(),
                "xmax": map_extent.xMaximum(),
                "ymax": map_extent.yMaximum(),
            },
            "layers_rendered": len(render_layers),
        })
