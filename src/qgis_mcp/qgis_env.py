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
    "C:\\OSGeo4W\\apps\\qgis-ltr",
    "C:\\OSGeo4W64\\apps\\qgis-ltr",
    "%LOCALAPPDATA%\\Programs\\OSGeo4W\\apps\\qgis",
    "%LOCALAPPDATA%\\Programs\\OSGeo4W\\apps\\qgis-ltr",
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
            expanded = os.path.expandvars(pattern)
            if "*" in expanded:
                matches = sorted(_glob.glob(expanded), reverse=True)
                for match in matches:
                    python_dir = Path(match) / "python"
                    if python_dir.exists():
                        return match
            else:
                python_dir = Path(expanded) / "python"
                if python_dir.exists():
                    return expanded

    elif sys.platform.startswith("linux"):
        for path in _LINUX_QGIS_PATHS:
            python_dir = Path(path) / "share" / "qgis" / "python"
            if python_dir.exists():
                return path

    return None


def _is_osgeo4w(qgis_path: Path) -> bool:
    """Check if this is an OSGeo4W installation structure."""
    parent = qgis_path.parent
    grandparent = parent.parent if parent.name == "apps" else None
    return grandparent is not None and (grandparent / "bin" / "o4w_env.bat").exists()


def _get_osgeo4w_root(qgis_path: Path) -> Path:
    """Get the OSGeo4W root directory."""
    if qgis_path.parent.name == "apps":
        return qgis_path.parent.parent
    return qgis_path


def _setup_qgis_environment(qgis_path: str) -> None:
    """Configure environment variables so QGIS modules can be imported."""
    qgis_root = Path(qgis_path)

    if sys.platform == "win32":
        # Detect OSGeo4W installation
        if _is_osgeo4w(qgis_root):
            osgeo4w_root = _get_osgeo4w_root(qgis_root)
            _setup_osgeo4w_environment(osgeo4w_root, qgis_root)
        else:
            _setup_standalone_windows(qgis_root)

    elif sys.platform.startswith("linux"):
        python_path = qgis_root / "share" / "qgis" / "python"
        if python_path.exists() and str(python_path) not in sys.path:
            sys.path.insert(0, str(python_path))

    os.environ["QGIS_PREFIX_PATH"] = str(qgis_root)


def _setup_osgeo4w_environment(osgeo4w_root: Path, qgis_app: Path) -> None:
    """Set up environment for an OSGeo4W QGIS installation."""
    root = str(osgeo4w_root)
    os.environ["OSGEO4W_ROOT"] = root

    # PATH - OSGeo4W bin must come first
    path_parts = [f"{root}\\bin"]
    # Additional paths from etc/ini scripts
    path_parts.append(f"{root}\\apps\\Python312\\Scripts")
    path_parts.append(f"{root}\\apps\\qgis-ltr\\bin")
    path_parts.append(f"{root}\\apps\\qt5\\bin")
    path_parts.append(os.environ.get("PATH", ""))
    os.environ["PATH"] = ";".join(path_parts)

    # Python home - critical for finding stdlib
    python_home = root + "\\apps\\Python312"
    if Path(python_home).exists():
        os.environ["PYTHONHOME"] = python_home
        # Also add stdlib to sys.path for import resolution
        for subdir in ("", "Lib", "Lib\\site-packages", "DLLs"):
            p = python_home + ("\\" + subdir if subdir else "")
            if Path(p).exists() and p not in sys.path:
                sys.path.insert(0, p)

    # QGIS Python modules
    qgis_python = qgis_app / "python"
    if qgis_python.exists() and str(qgis_python) not in sys.path:
        sys.path.insert(0, str(qgis_python))
        os.environ["PYTHONPATH"] = str(qgis_python) + ";" + os.environ.get("PYTHONPATH", "")

    # QGIS plugins (needed for processing)
    plugins_path = qgis_app / "python" / "plugins"
    if plugins_path.exists() and str(plugins_path) not in sys.path:
        sys.path.insert(0, str(plugins_path))

    # Qt5
    qt_plugins = root + "\\apps\\Qt5\\plugins"
    if Path(qt_plugins).exists():
        os.environ["QT_PLUGIN_PATH"] = qt_plugins

    # GDAL
    gdal_data = root + "\\apps\\gdal\\share\\gdal"
    if Path(gdal_data).exists():
        os.environ["GDAL_DATA"] = gdal_data
        os.environ["GDAL_DRIVER_PATH"] = root + "\\apps\\gdal\\lib\\gdalplugins"

    # PROJ
    proj_data = root + "\\share\\proj"
    if Path(proj_data).exists():
        os.environ["PROJ_DATA"] = proj_data
        os.environ["PROJ_LIB"] = proj_data

    # Misc
    os.environ["GDAL_FILENAME_IS_UTF8"] = "YES"
    os.environ["VSI_CACHE"] = "TRUE"
    os.environ["VSI_CACHE_SIZE"] = "1000000"
    os.environ["PYTHONUTF8"] = "1"


def _setup_standalone_windows(qgis_root: Path) -> None:
    """Set up environment for a standalone QGIS installation (non-OSGeo4W)."""
    python_path = qgis_root / "python"
    if python_path.exists() and str(python_path) not in sys.path:
        sys.path.insert(0, str(python_path))

    bin_path = qgis_root / "bin"
    os_paths = os.environ.get("PATH", "")
    if bin_path.exists() and str(bin_path) not in os_paths:
        os.environ["PATH"] = f"{bin_path};{os_paths}"

    qt_plugins = qgis_root / "apps" / "Qt5" / "plugins"
    if qt_plugins.exists():
        os.environ["QT_PLUGIN_PATH"] = str(qt_plugins)

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

        # Initialize processing framework for standalone use
        try:
            from qgis.analysis import QgsNativeAlgorithms
            QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
            # Also initialize the full processing plugin
            from processing.core.Processing import Processing
            Processing.initialize()
            logger.info("Processing framework initialized")
        except Exception as e:
            logger.warning(f"Processing initialization skipped: {e}")

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
