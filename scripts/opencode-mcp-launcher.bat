@echo off
REM Launcher for OpenCode MCP - sets up OSGeo4W env and runs qgis-mcp
set OSGEO4W_ROOT=C:\Users\dell\AppData\Local\Programs\OSGeo4W
set PYTHONHOME=%OSGEO4W_ROOT%\apps\Python312
set PYTHONPATH=%OSGEO4W_ROOT%\apps\qgis-ltr\python;%OSGEO4W_ROOT%\apps\qgis-ltr\python\plugins
set PATH=%OSGEO4W_ROOT%\bin;%OSGEO4W_ROOT%\apps\Python312\Scripts;%OSGEO4W_ROOT%\apps\qgis-ltr\bin;%OSGEO4W_ROOT%\apps\qt5\bin;%PATH%
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\Qt5\plugins
set GDAL_DATA=%OSGEO4W_ROOT%\apps\gdal\share\gdal
set PROJ_DATA=%OSGEO4W_ROOT%\share\proj
set GDAL_FILENAME_IS_UTF8=YES
set PYTHONUTF8=1
set QGIS_INSTALL_PATH=%OSGEO4W_ROOT%\apps\qgis-ltr

"%OSGEO4W_ROOT%\bin\python3.exe" -m qgis_mcp.server --qgis-path "%QGIS_INSTALL_PATH%" %*
