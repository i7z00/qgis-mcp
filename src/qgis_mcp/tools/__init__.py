"""Tool registration aggregator."""

from . import project as _project
from . import features as _features
from . import spatial as _spatial
from . import processing as _processing
from . import raster as _raster
from . import export as _export

_registry = {
    "project": _project.register_tools,
    "features": _features.register_tools,
    "spatial": _spatial.register_tools,
    "processing": _processing.register_tools,
    "raster": _raster.register_tools,
    "export": _export.register_tools,
}


def register_all(mcp) -> None:
    """Register all tool modules on the given FastMCP instance."""
    for name, register_fn in _registry.items():
        register_fn(mcp)
