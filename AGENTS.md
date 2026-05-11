# AGENTS.md — QGIS MCP Server

Agent-focused guidance for working with this codebase.

## Environment

- **OS**: Windows (win32)
- **QGIS**: 3.40 LTR via OSGeo4W
  - Install: `C:\Users\dell\AppData\Local\Programs\OSGeo4W\apps\qgis-ltr`
  - Bundled Python: 3.12.12 (ABI-incompatible with system Python)
  - GRASS: `C:\Users\dell\AppData\Local\Programs\OSGeo4W\apps\grass\grass84`
- **Launcher**: `scripts/opencode-mcp-launcher.bat` sets up OSGeo4W env before starting server

## Critical Constraints

### Headless QGIS ≠ QGIS Desktop
The MCP server runs QGIS **without a GUI** (`QgsApplication([], False)`). This has permanent consequences:

1. **`QgsProject.write()` omits `<mapcanvas>`**
   - Desktop requires `<mapcanvas>` to know where to zoom. Without it → **white/blank canvas**.
   - **ALWAYS use the `save_project` tool** (which auto-injects canvas). Never call `QgsProject.instance().write()` directly.
   - If you must write directly, post-process the XML to add `<mapcanvas>` with combined layer extent.

2. **File paths**
   - Windows file locking means `os.remove()` can fail with `PermissionError`. Use retry loops or defer cleanup.
   - Prefer **absolute paths** in `.qgs` files unless the project is strictly colocated with data.
   - GeoPackage multi-layer syntax: `path.gpkg|layername=layer_name` — handled by `_parse_layer_path()`.

3. **GRASS vs SAGA**
   - SAGA is **not installed** in this OSGeo4W setup. Use GRASS algorithms (`grass:r.watershed`, `grass:r.water.outlet`, etc.).
   - Always call `Processing.initialize()` and register `QgsNativeAlgorithms` before using processing tools.

4. **QGIS 3.40 API removals**
   - `QgsCoordinateReferenceSystem.isProjected()` — removed. Use `!isGeographic()` instead.
   - `hasVerticalAxisInverted()` — removed. Do not use.
   - When in doubt, check `qgis.core` API docs for 3.40 LTR.

## Code Patterns

### Saving a project (GUI-compatible)
```python
# CORRECT — injects canvas automatically
save_project("C:/path/to/project.qgs", make_paths_absolute=True)

# WRONG — produces white canvas in Desktop
QgsProject.instance().write("C:/path/to/project.qgs")
```

### Layer ID resolution in processing
The `run_processing` tool accepts any UUID string for layer references, not just `layer_id_` prefix. It resolves via `QgsProject.instance().mapLayer(layer_id)`.

### Post-processing raster outputs
GRASS `r.mapcalc` and GDAL raster calculator may produce `float32(FLT_MAX)` as nodata. Filter with `arr < 1000` or similar before statistics.

## Verification Protocol

Before declaring a QGIS deliverable "complete":

1. **Project file**: Call `validate_project` to check canvas, paths, CRS.
2. **If the user will open in Desktop**: Confirm `save_project` was used (not raw write).
3. **Raster outputs**: Verify dimensions match the input DEM (reprojection can change extents).

## File Locations (Reference)

- Server code: `src/qgis_mcp/tools/project.py`
- Processing tools: `src/qgis_mcp/tools/processing.py`
- Environment setup: `src/qgis_mcp/qgis_env.py`
- Launcher: `scripts/opencode-mcp-launcher.bat`
