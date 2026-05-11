# QGIS MCP Server

Connect QGIS spatial analysis to AI agentic environments (Claude Code, Codex, OpenCode) via the Model Context Protocol.

## Features

- **Layer Management**: Load and manage vector/raster layers
- **Feature Queries**: Query features with attribute and spatial filters
- **Spatial Analysis**: Buffer, spatial queries, reprojection, area/length
- **Processing**: Run QGIS processing algorithms (1000+ available)
- **Raster Analysis**: Sample values, compute statistics, clip rasters
- **Map Export**: Render and export map images

## Installation

```bash
pip install qgis-mcp
```

Requires QGIS 3.x installed on the system.

## Quick Start

### For Claude Code / Codex / OpenCode

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "qgis": {
      "command": "qgis-mcp",
      "args": ["--qgis-path", "/path/to/qgis"]
    }
  }
}
```

### HTTP Mode

```bash
qgis-mcp --http --port 8000
```

## Tools

| Tool | Description |
|------|-------------|
| `load_project` | Load a QGIS project file |
| `load_vector_layer` | Load a vector layer from file |
| `load_raster_layer` | Load a raster layer from file |
| `list_layers` | List all loaded layers |
| `get_layer_info` | Get detailed layer metadata |
| `get_features` | Query features with filters |
| `get_feature_count` | Count features in a layer |
| `get_field_values` | Get field values |
| `get_extent` | Get layer/project extent |
| `buffer` | Create buffer geometries |
| `spatial_query` | Select features by spatial relationship |
| `reproject_layer` | Reproject to different CRS |
| `get_crs_info` | Get CRS details |
| `calculate_field` | Calculate field with QGIS expressions |
| `calculate_area_length` | Compute area/length statistics |
| `list_algorithms` | List processing algorithms |
| `get_algorithm_help` | Get algorithm parameter details |
| `run_processing` | Execute processing algorithms |
| `sample_raster` | Sample raster values at points |
| `get_raster_statistics` | Get raster band statistics |
| `clip_raster_by_extent` | Clip raster by bounding box |
| `export_map_image` | Export map as PNG image |

## Resources

- `qgis://layers` - Current layers
- `qgis://layer/{layer_id}` - Layer details
- `qgis://algorithms` - Available processing algorithms

## Environment Variables

- `QGIS_INSTALL_PATH` - Path to QGIS installation directory
