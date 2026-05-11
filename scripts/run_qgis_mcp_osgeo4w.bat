@echo off
REM QGIS MCP Server Launcher for OSGeo4W
REM Sets up the OSGeo4W environment and runs the MCP server

call "%~dp0..\..\..\..\AppData\Local\Programs\OSGeo4W\bin\o4w_env.bat"
call "%OSGEO4W_ROOT%\bin\python-qgis-ltr.bat" -m qgis_mcp.server %*
