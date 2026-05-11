"""
QGIS MCP Server - Main entry point.

Connects QGIS spatial analysis capabilities to AI agentic environments
(Claude Code, Codex, OpenCode) via the Model Context Protocol.

Usage:
    qgis-mcp                    # Start with stdio transport (for local agents)
    qgis-mcp --http             # Start with streamable HTTP transport
    qgis-mcp --http --port 8080 # Start HTTP on custom port
    qgis-mcp --qgis-path /path  # Specify QGIS installation path
"""

import argparse
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("qgis-mcp")

# Pre-import the mcp package to ensure it's installed
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print(
        "Error: MCP Python SDK not installed. Install with: pip install 'mcp[cli]'",
        file=sys.stderr,
    )
    sys.exit(1)

from .qgis_env import init_qgis, exit_qgis, is_qgis_available
from .tools import register_all as register_all_tools
from .resources import register_resources
from .prompts import register_prompts


def create_server() -> FastMCP:
    """Create and configure the QGIS MCP server."""
    mcp = FastMCP(
        "QGIS Spatial Analysis",
        instructions="""QGIS MCP Server provides spatial analysis and GIS data manipulation capabilities.

## Capabilities
- **Layer Management**: Load, inspect, and manage vector/raster layers
- **Feature Queries**: Query features with attribute filters and spatial filters
- **Spatial Analysis**: Buffer, spatial queries, reprojection, area/length calculation
- **Processing**: Run hundreds of QGIS processing algorithms (buffer, clip, dissolve, etc.)
- **Raster Analysis**: Sample values, compute statistics, clip rasters
- **Map Export**: Render and export map images
- **Project Management**: Load and inspect QGIS project files

## Getting Started
1. Use `list_layers` to see what's loaded
2. Use `get_layer_info` with a layer ID for detailed metadata
3. Use `get_features` to query vector data
4. Use `list_algorithms` to discover processing capabilities
5. Use `run_processing` to execute spatial analysis algorithms""",
    )

    # Register all components
    register_all_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    return mcp


def main():
    """Entry point for the qgis-mcp CLI."""
    parser = argparse.ArgumentParser(
        description="QGIS MCP Server - Connect QGIS to AI agentic environments",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Start with Streamable HTTP transport (for remote agents)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: 8000)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--qgis-path",
        help="Path to QGIS installation (overrides QGIS_INSTALL_PATH env var)",
    )
    parser.add_argument(
        "--no-qgis",
        action="store_true",
        help="Start without initializing QGIS (limited functionality)",
    )

    args = parser.parse_args()

    # Initialize QGIS
    if not args.no_qgis:
        qgis_path = args.qgis_path or os.environ.get("QGIS_INSTALL_PATH")
        success = init_qgis(qgis_path)
        if not success:
            logger.warning(
                "QGIS not found. Set QGIS_INSTALL_PATH or use --qgis-path. "
                "Server will start with limited capabilities."
            )
    else:
        logger.info("Starting without QGIS (--no-qgis flag)")

    # Create the server
    server = create_server()

    # Choose transport
    if args.http:
        transport = "streamable-http"
        logger.info(f"Starting QGIS MCP Server on HTTP: {args.host}:{args.port}")
        server.settings.host = args.host
        server.settings.port = args.port
    else:
        transport = "stdio"
        logger.info("Starting QGIS MCP Server on STDIO")

    try:
        server.run(transport=transport)
    finally:
        exit_qgis()


if __name__ == "__main__":
    main()
