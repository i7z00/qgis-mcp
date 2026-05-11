import sys, os
sys.path.insert(0, r"C:\Users\dell\qgis-mcp\src")

# Set GRASS environment BEFORE initializing QGIS
os.environ["GISBASE"] = r"C:\Users\dell\AppData\Local\Programs\OSGeo4W\apps\grass\grass84"
# Check if the path exists
import pathlib
gb = pathlib.Path(os.environ["GISBASE"])
print(f"GISBASE={os.environ['GISBASE']}")
print(f"  exists={gb.exists()}")
print(f"  bin exists={(gb / 'bin').exists()}")
print(f"  scripts exists={(gb / 'scripts').exists()}")

from qgis_mcp.qgis_env import init_qgis
init_qgis()
from qgis.core import QgsApplication

reg = QgsApplication.processingRegistry()
for p in reg.providers():
    if p.name() == "GRASS":
        algs = p.algorithms()
        print(f"GRASS algorithms: {len(algs)}")
        for a in algs[:3]:
            print(f"  {a.id()}")
