"""
QGIS environment initialization for standalone Python scripts.

Responsible for locating the QGIS installation and initializing
the QgsApplication in headless mode for use by the MCP server.
"""

import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger("qgis-mcp")

_qgis_initialized = False
_qgis_app = None

# Common QGIS installation paths on Windows
_WINDOWS_QGIS_PATHS = [
    "C:\\OSGeo4W\\apps\\qgis",
    "C:\\OSGeo4W64\\apps\\qgis",
    "C:\\Program Files\\QGIS *",
    "C:\\Program Files (x86)\\QGIS *",
]

# Common QGIS installation paths on Linux
_LINUX_QGIS_PATHS = [
    "/usr",
    "/usr/share/qgis",
]


def _find_qgis_path(custom_path: str | None = None) -> str | None:
    """
    Detect QGIS installation path.

    Resolution order:
    1. QGIS_INSTALL_PATH environment variable
    2. Custom path argument
    3. Common platform-specific paths
    """
    env_path = os.environ.get("QGIS_INSTALL_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    if custom_path and Path(custom_path).exists():
        return custom_path

    if sys.platform == "win32":
        import glob as _glob

        for pattern in _WINDOWS_QGIS_PATHS:
            if "*" in pattern:
                matches = sorted(_glob.glob(pattern), reverse=True)
                for match in matches:
                    python_dir = Path(match) / "python"
                    if python_dir.exists():
                        return match
            else:
                python_dir = Path(pattern) / "python"
                if python_dir.exists():
                    return pattern

    elif sys.platform.startswith("linux"):
        for path in _LINUX_QGIS_PATHS:
            python_dir = Path(path) / "share" / "qgis" / "python"
            if python_dir.exists():
                return path

    return None


def _setup_qgis_environment(qgis_path: str) -> None:
    """Configure environment variables so QGIS modules can be imported."""
    qgis_root = Path(qgis_path)

    if sys.platform == "win32":
        # QGIS Python modules
        python_path = qgis_root / "python"
        if python_path.exists() and str(python_path) not in sys.path:
            sys.path.insert(0, str(python_path))

        # QGIS DLLs
        bin_path = qgis_root / "bin"
        apps_path = qgis_root / "apps" / "qgis" / "bin"
        os_paths = os.environ.get("PATH", "")
        if bin_path.exists() and str(bin_path) not in os_paths:
            os.environ["PATH"] = f"{bin_path};{os_paths}"
        if apps_path.exists() and str(apps_path) not in os_paths:
            os.environ["PATH"] = f"{apps_path};{os.environ['PATH']}"

        # Qt plugins
        qt_plugins = qgis_root / "apps" / "Qt5" / "plugins"
        if qt_plugins.exists():
            os.environ["QT_PLUGIN_PATH"] = str(qt_plugins)

        # GDAL/PROJ data
        share_path = qgis_root / "share"
        if share_path.exists():
            if "GDAL_DATA" not in os.environ:
                gdal_data = share_path / "gdal"
                if gdal_data.exists():
                    os.environ["GDAL_DATA"] = str(gdal_data)
            if "PROJ_LIB" not in os.environ:
                proj_lib = share_path / "proj"
                if proj_lib.exists():
                    os.environ["PROJ_LIB"] = str(proj_lib)

    elif sys.platform.startswith("linux"):
        python_path = qgis_root / "share" / "qgis" / "python"
        if python_path.exists() and str(python_path) not in sys.path:
            sys.path.insert(0, str(python_path))

    os.environ["QGIS_PREFIX_PATH"] = str(qgis_root)


def init_qgis(qgis_path: str | None = None) -> bool:
    """
    Initialize QGIS application in headless mode.

    Returns True if QGIS was successfully initialized, False otherwise.
    Safe to call multiple times - subsequent calls are no-ops.
    """
    global _qgis_initialized, _qgis_app

    if _qgis_initialized:
        return True

    qgis_root = _find_qgis_path(qgis_path)
    if not qgis_root:
        logger.warning(
            "QGIS installation not found. Set QGIS_INSTALL_PATH environment "
            "variable or pass qgis_path parameter to init_qgis(). "
            "Server will start without QGIS spatial analysis capabilities."
        )
        return False

    try:
        _setup_qgis_environment(qgis_root)

        from qgis.core import QgsApplication

        QgsApplication.setPrefixPath(str(qgis_root), True)
        _qgis_app = QgsApplication([], False)
        _qgis_app.initQgis()

        _qgis_initialized = True
        logger.info(f"QGIS initialized successfully from: {qgis_root}")
        return True

    except ImportError as e:
        logger.warning(
            f"Could not import QGIS modules: {e}. "
            "Ensure QGIS is installed and QGIS_INSTALL_PATH is set correctly."
        )
        return False
    except Exception as e:
        logger.error(f"QGIS initialization failed: {e}")
        return False


def exit_qgis() -> None:
    """Cleanly shut down QGIS application."""
    global _qgis_initialized, _qgis_app

    if _qgis_app is not None:
        try:
            _qgis_app.exitQgis()
        except Exception:
            pass
        _qgis_app = None

    _qgis_initialized = False


def is_qgis_available() -> bool:
    """Check if QGIS has been successfully initialized."""
    return _qgis_initialized


def require_qgis() -> None:
    """Raise RuntimeError if QGIS is not available."""
    if not _qgis_initialized:
        raise RuntimeError(
            "QGIS is not available. Set QGIS_INSTALL_PATH environment "
            "variable and ensure QGIS is installed. See documentation."
        )
