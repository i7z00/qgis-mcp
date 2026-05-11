# QGIS MCP Server

Connect QGIS spatial analysis to AI agentic environments (Claude Code, Codex, OpenCode) via the Model Context Protocol.

## Overview

The QGIS MCP Server exposes QGIS's spatial analysis capabilities as MCP tools, resources, and prompts. AI agents can load GIS data, query features, perform spatial analysis, run processing algorithms, analyze rasters, and export maps — all through natural language interaction.

## Architecture

```
AI Agent (Claude Code / Codex / OpenCode)
  │
  ├─ MCP Client ◄─── STDIO or HTTP ───► MCP Server (qgis-mcp)
  │                                          │
  │                                     QGIS Core (headless)
  │                                     ├── Vector layers
  │                                     ├── Raster layers
  │                                     ├── Processing algorithms
  │                                     └── Map rendering
```

- **Headless QGIS**: Uses `QgsApplication([], False)` — no GUI required
- **Auto-discovery**: Finds QGIS installation from env vars or common paths
- **Degrade gracefully**: `--no-qgis` mode allows testing without QGIS installed
- **Dual transport**: STDIO (local agents) and HTTP (remote agents)

## Installation

```bash
pip install qgis-mcp
```

**Prerequisites**: [QGIS](https://qgis.org/) 3.x installed on the system with Python bindings.

For development:

```bash
git clone <repo-url>
cd qgis-mcp
uv venv
uv pip install "mcp[cli]>=1.0.0" pydantic
uv pip install pytest pytest-asyncio      # for tests
```

## Quick Start

### 1. Find your QGIS installation path

Open QGIS Desktop, open the Python console (`Plugins > Python Console`), and run:

```python
from qgis.core import QgsApplication
print(QgsApplication.prefixPath())
```

Common paths:
- **Windows**: `C:\OSGeo4W\apps\qgis` or `C:\Program Files\QGIS 3.x`
- **Linux**: `/usr`
- **macOS**: `/Applications/QGIS.app/Contents/MacOS`

### 2. Configure your AI agent

#### Claude Code / OpenCode

```json
{
  "mcpServers": {
    "qgis": {
      "command": "qgis-mcp",
      "args": ["--qgis-path", "/path/to/qgis"],
      "env": {
        "QGIS_INSTALL_PATH": "/path/to/qgis"
      }
    }
  }
}
```

#### Claude Desktop

```json
{
  "mcpServers": {
    "qgis": {
      "command": "python",
      "args": ["-m", "qgis_mcp.server", "--qgis-path", "C:\\OSGeo4W\\apps\\qgis"]
    }
  }
}
```

### 3. HTTP mode (for remote agents)

```bash
qgis-mcp --http --port 8000 --host 0.0.0.0
```

### 4. Testing without QGIS

```bash
qgis-mcp --no-qgis
# Server starts but spatial analysis tools return helpful errors
```

## Tools Reference

### Layer Management (6 tools)

| Tool | Description |
|------|-------------|
| `load_project` | Load a `.qgs`/`.qgz` QGIS project file |
| `load_vector_layer` | Load vector from file (SHP, GeoJSON, GPKG, etc.) |
| `load_raster_layer` | Load raster from file (GeoTIFF, etc.) |
| `list_layers` | List all loaded layers with metadata |
| `get_layer_info` | Get detailed layer metadata (fields, CRS, extent) |
| `remove_layer` | Remove a layer from the project |

### Feature Queries (3 tools)

| Tool | Description |
|------|-------------|
| `get_features` | Query features with attribute filter, bbox, pagination. Returns GeoJSON. |
| `get_feature_count` | Count features, optionally with attribute filter |
| `get_field_values` | Get unique or all values for a field |

### Spatial Analysis (7 tools)

| Tool | Description |
|------|-------------|
| `get_extent` | Get extent of layers or full project |
| `buffer` | Create buffer geometries (with dissolve option) |
| `spatial_query` | Select features by spatial predicate (intersects, contains, within, etc.) |
| `reproject_layer` | Reproject to a different CRS |
| `get_crs_info` | Get CRS details (WKT, Proj4, units) |
| `calculate_field` | Add/calculate fields using QGIS expressions |
| `calculate_area_length` | Compute area/length statistics for vector layers |

### Processing (3 tools)

| Tool | Description |
|------|-------------|
| `list_algorithms` | List available processing algorithms (filterable, 1000+ total) |
| `get_algorithm_help` | Get detailed parameter info for any algorithm |
| `run_processing` | Execute any QGIS processing algorithm |

### Raster Analysis (3 tools)

| Tool | Description |
|------|-------------|
| `sample_raster` | Sample raster values at point coordinates |
| `get_raster_statistics` | Get band statistics (min, max, mean, stddev) |
| `clip_raster_by_extent` | Clip raster by bounding box |

### Export (1 tool)

| Tool | Description |
|------|-------------|
| `export_map_image` | Export current map view as PNG (configurable size, extent, layers, DPI) |

## Resources

| URI | Description |
|-----|-------------|
| `qgis://layers` | Current layers as JSON |
| `qgis://layer/{layer_id}` | Individual layer details |
| `qgis://algorithms` | All available processing algorithms |

## Prompts

| Prompt | Purpose |
|--------|---------|
| `spatial_analysis_workflow` | Guided workflow for spatial analysis tasks |
| `layer_exploration` | Systematic layer data exploration guide |
| `map_export_workflow` | Map creation and export workflow |

## Example: Swellendam Property Search

This example from the [QGIS Training Manual](https://docs.qgis.org/latest/en/docs/training_manual/) finds residential properties meeting 5 criteria:

1. Within 1km of a school
2. Larger than 100m²
3. Within 50m of a main road
4. Within 500m of a restaurant
5. Located in Swellendam, South Africa

### AI Agent Interaction

```
User: Find properties in Swellendam matching these criteria...

Agent calls tools in sequence:
1. load_vector_layer(path="training_data.gpkg|layername=buildings")
2. load_vector_layer(path="training_data.gpkg|layername=roads")
3. load_vector_layer(path="training_data.gpkg|layername=schools")
4. load_vector_layer(path="training_data.gpkg|layername=restaurants")
5. reproject_layer(buildings_id, target_crs="EPSG:32734")
6. buffer(roads_id, distance=50, dissolve=True)
7. buffer(schools_id, distance=1000, dissolve=True)
8. run_processing("native:intersection", road_buffer, school_buffer)
9. spatial_query(buildings, intersection_area, predicate="intersects")
10. buffer(restaurants_id, distance=500, dissolve=True)
11. spatial_query(filtered_buildings, restaurant_buffer, predicate="intersects")
12. calculate_area_length(filtered_buildings)
13. export_map_image(layers=filtered_buildings, width=1200, height=900)
```

Download the training data:
```bash
wget https://github.com/qgis/QGIS-Training-Data/archive/release_3.44.zip
unzip release_3.44.zip
```

## Testing

```bash
# Tool schema validation (works without QGIS)
uv run pytest tests/test_server.py -v

# With QGIS installed, also run:
uv run pytest tests/ -v

# Run scenario evaluations
uv run python -c "
from tests.scenarios import ALL_SCENARIOS
from tests.test_evaluation import run_scenario_schema_only
for s in ALL_SCENARIOS:
    print(run_scenario_schema_only(s).summary())
"
```

Test results: **18/18 tests pass** (schema validation, error handling, resource/prompt registration). All 3 scenarios verified with 31/31 workflow steps.

## CLI Reference

```
qgis-mcp [OPTIONS]

Options:
  --http              Start with Streamable HTTP transport (default: stdio)
  --port PORT         HTTP port (default: 8000)
  --host HOST         HTTP host (default: 127.0.0.1)
  --qgis-path PATH    Path to QGIS installation
  --no-qgis           Start without QGIS (limited functionality)
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `QGIS_INSTALL_PATH` | Path to QGIS installation directory |
| `QGIS_PREFIX_PATH` | Set automatically during initialization |

## Project Structure

```
qgis-mcp/
├── src/qgis_mcp/
│   ├── server.py          # MCP server entry point + CLI
│   ├── qgis_env.py        # QGIS initialization & path detection
│   ├── tools/             # Tool implementations
│   │   ├── project.py     # Layer management
│   │   ├── features.py    # Feature queries
│   │   ├── spatial.py     # Spatial analysis
│   │   ├── processing.py  # Processing algorithms
│   │   ├── raster.py      # Raster analysis
│   │   └── export.py      # Map export
│   ├── resources/         # Resource definitions
│   └── prompts/           # Prompt templates
├── tests/
│   ├── conftest.py        # Fixtures + synthetic data
│   ├── test_server.py     # Server/tool schema tests (18)
│   ├── test_evaluation.py # Scenario evaluation harness
│   └── scenarios.py       # Test scenario definitions (3)
├── test_data/             # QGIS training data (not tracked)
└── pyproject.toml
```

## License

MIT
