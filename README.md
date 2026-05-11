# QGIS MCP Server

Connect QGIS spatial analysis to AI agentic environments (Claude Code, Codex, OpenCode) via the Model Context Protocol.

## Overview

The QGIS MCP Server exposes QGIS's spatial analysis capabilities as MCP tools, resources, and prompts. AI agents can load GIS data, query features, perform spatial analysis, run processing algorithms, analyze rasters, and export maps — all through natural language interaction.

> **For AI agents / developers**: See [`AGENTS.md`](./AGENTS.md) for critical environment constraints, code patterns, and the verification protocol.

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

- **Headless QGIS**: Uses `QgsApplication([], False)` — no GUI required. Projects saved from headless QGIS omit `<mapcanvas>`, which causes a **white/blank canvas** in QGIS Desktop. Always use the `save_project` tool (auto-injects canvas) instead of raw `QgsProject.write()`.
- **Auto-discovery**: Finds QGIS installation from env vars or common paths
- **Degrade gracefully**: `--no-qgis` mode allows testing without QGIS installed
- **Dual transport**: STDIO (local agents) and HTTP (remote agents)

## Installation

### Prerequisites

- **QGIS 3.x** installed ([download](https://qgis.org/download/))
- **Python 3.10+** with pip
- **Git** (for source install)

### Step 1: Install QGIS

Choose your platform:

| OS | Recommended method |
|----|--------------------|
| **Windows** | [OSGeo4W Network Installer](https://qgis.org/download/) — select `qgis-ltr` (Desktop) |
| **Linux** | `sudo apt install qgis` (Debian/Ubuntu) or your distro's package manager |
| **macOS** | [QGIS macOS Installer](https://qgis.org/download/macos/) or `brew install qgis` |

### Step 2: Install qgis-mcp

#### Option A: From GitHub (recommended)

```bash
pip install git+https://github.com/i7z00/qgis-mcp.git
```

#### Option B: From local source

```bash
git clone https://github.com/i7z00/qgis-mcp.git
cd qgis-mcp
pip install -e .
```

#### Option C: Development install

```bash
git clone https://github.com/i7z00/qgis-mcp.git
cd qgis-mcp
uv venv
uv pip install -e ".[dev]"
```

### Step 3: Platform-specific setup

#### Windows (OSGeo4W)

OSGeo4W bundles its own Python. qgis-mcp must run with QGIS's Python to load its C extensions. A launcher script is provided:

```cmd
scripts\opencode-mcp-launcher.bat
```

This sets `PYTHONHOME`, `PATH`, `QT_PLUGIN_PATH`, `GDAL_DATA`, and `PROJ_DATA` automatically, then starts the server using QGIS's bundled `python3.exe`.

If you installed QGIS via the standalone installer (not OSGeo4W), set the environment variable:

```cmd
set QGIS_INSTALL_PATH=C:\Program Files\QGIS 3.40
python -m qgis_mcp.server
```

#### Linux

```bash
# Find your QGIS Python path
QGIS_PATH=$(python3 -c "from qgis.core import QgsApplication; print(QgsApplication.prefixPath())" 2>/dev/null || echo "/usr")

# Run with auto-detection
python3 -m qgis_mcp.server --qgis-path "$QGIS_PATH"

# Or set environment variable
export QGIS_INSTALL_PATH=/usr
python3 -m qgis_mcp.server
```

#### macOS

```bash
# Homebrew
export QGIS_INSTALL_PATH=/Applications/QGIS.app/Contents/MacOS
python3 -m qgis_mcp.server

# Or auto-detect
python3 -m qgis_mcp.server --qgis-path /Applications/QGIS.app/Contents/MacOS
```

### Step 4: Verify

```bash
python -m qgis_mcp.server --no-qgis --help
```

Should print the CLI help. Add `--qgis-path` to test with full spatial analysis.

### Step 5: Configure your AI agent

#### OpenCode — Global Setup (Recommended)

Create `C:\Users\%USERNAME%\.opencode\opencode.jsonc` (global config, works from any directory):

**Windows (OSGeo4W)** — uses the bundled launcher:
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "qgis": {
      "type": "local",
      "command": ["cmd", "/c", "C:\\Users\\dell\\qgis-mcp\\scripts\\opencode-mcp-launcher.bat"],
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

**Linux / macOS / Windows (standalone QGIS)** — uses system Python:
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "qgis": {
      "type": "local",
      "command": ["python3", "-m", "qgis_mcp.server", "--qgis-path", "/path/to/qgis"],
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

> **Why global?** The `.opencode/opencode.jsonc` in your project root only works when the AI starts in that specific folder. The global config at `~/.opencode/opencode.jsonc` makes the QGIS MCP server available from **any** working directory.

#### OpenCode — Per-Project Setup

If you prefer, you can also place the same config in `.opencode/opencode.jsonc` inside your project root (e.g., `C:\Users\dell\documents\qgis\my-project\.opencode\opencode.jsonc`). This overrides the global config for that project.

#### Claude Code / Claude Desktop

Claude Code uses a different config format. Add to your Claude settings:

```json
{
  "mcpServers": {
    "qgis": {
      "command": "cmd",
      "args": ["/c", "C:\\Users\\dell\\qgis-mcp\\scripts\\opencode-mcp-launcher.bat"],
      "env": {
        "QGIS_INSTALL_PATH": "C:\\Users\\dell\\AppData\\Local\\Programs\\OSGeo4W\\apps\\qgis-ltr"
      }
    }
  }
}
```

For Claude Desktop on Windows, the config file is typically at:
`%APPDATA%\Claude\settings.json`

### Step 6: HTTP mode (optional, for remote agents)

```bash
python -m qgis_mcp.server --http --port 8000 --host 0.0.0.0
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'qgis'` | QGIS not installed or QGIS_INSTALL_PATH is wrong. Run `QgsApplication.prefixPath()` in QGIS Python Console to find the path. |
| `DLL load failed` (Windows) | Use the OSGeo4W launcher script or set `PYTHONHOME` and `PATH` to point to QGIS's Python and bin directories. |
| `Processing plugin has not been loaded` | Processing framework not initialized. The server auto-initializes it — ensure QGIS is fully installed with processing plugin. |
| `qgis_mcp` not found | Install with `pip install git+https://github.com/i7z00/qgis-mcp.git` or `pip install -e .` from source. |
| Agent doesn't know about QGIS in other folders | Ensure global config exists at `~/.opencode/opencode.jsonc` (not just in project root). See Step 5 above. |

### Cross-Project Skill (Optional)

For AI agents that support skills (Claude Code, etc.), a reusable skill file is available at:
```
C:\Users\dell\.claude\skills\qgis-mcp\SKILL.md
```

Load it in any session by asking the agent: *"Load the qgis-mcp skill"* or *"Use the QGIS MCP skill"*. This injects the critical rules (use `save_project`, not raw write; call `validate_project`; etc.) even when the agent is working outside the `qgis-mcp` directory.

## Tools Reference

### Layer Management (8 tools)

| Tool | Description |
|------|-------------|
| `load_project` | Load a `.qgs`/`.qgz` QGIS project file |
| `load_vector_layer` | Load vector from file (SHP, GeoJSON, GPKG, etc.) |
| `load_raster_layer` | Load raster from file (GeoTIFF, etc.) |
| `list_layers` | List all loaded layers with metadata |
| `get_layer_info` | Get detailed layer metadata (fields, CRS, extent) |
| `remove_layer` | Remove a layer from the project |
| `save_project` | Save project with auto-injected `<mapcanvas>` for Desktop compatibility |
| `validate_project` | Check project health (CRS, paths, extents) before saving |

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
# Windows (PowerShell)
Invoke-WebRequest -Uri "https://github.com/qgis/QGIS-Training-Data/archive/release_3.44.zip" -OutFile "training_data.zip"

# Linux/macOS
curl -L -o training_data.zip https://github.com/qgis/QGIS-Training-Data/archive/release_3.44.zip

# Extract
unzip training_data.zip
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
python -m qgis_mcp.server [OPTIONS]

Options:
  --http              Start with Streamable HTTP transport (default: stdio)
  --port PORT         HTTP port (default: 8000)
  --host HOST         HTTP host (default: 127.0.0.1)
  --qgis-path PATH    Path to QGIS installation
  --no-qgis           Start without QGIS (limited functionality)
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `QGIS_INSTALL_PATH` | Yes | Path to QGIS installation directory |
| `PYTHONHOME` | OSGeo4W only | Path to QGIS's bundled Python (e.g. `OSGeo4W\apps\Python312`) |
| `QT_PLUGIN_PATH` | OSGeo4W only | Path to Qt5 plugins (e.g. `OSGeo4W\apps\Qt5\plugins`) |
| `GDAL_DATA` | OSGeo4W only | Path to GDAL data (e.g. `OSGeo4W\apps\gdal\share\gdal`) |
| `PROJ_DATA` or `PROJ_LIB` | OSGeo4W only | Path to PROJ data (e.g. `OSGeo4W\share\proj`) |
| `QGIS_PREFIX_PATH` | Auto | Set automatically during initialization |
| `PYTHONPATH` | Auto | QGIS Python modules path, set automatically |

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
