"""Inspect Package_A data for QGIS assignment."""
import sys, json

sys.path.insert(0, r"C:\Users\dell\qgis-mcp\src")
from qgis_mcp.qgis_env import init_qgis
init_qgis()

from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject

DATA = r"C:\Users\dell\documents\qgis\test-assignment\assignment_data\Package_A"

# DEM
dem = QgsRasterLayer(f"{DATA}\\DEM_A.tif", "DEM_A")
print(f"DEM: valid={dem.isValid()}, CRS={dem.crs().authid()}")
print(f"  Extent: {dem.extent()}")
print(f"  Size: {dem.width()}x{dem.height()}, bands={dem.bandCount()}")
stats = dem.dataProvider().bandStatistics(1)
print(f"  Elevation: min={stats.minimumValue:.1f}, max={stats.maximumValue:.1f}, mean={stats.mean:.1f}")

# Land Cover
lc = QgsRasterLayer(f"{DATA}\\LandCover_A.tif", "LandCover_A")
print(f"\nLandCover: valid={lc.isValid()}, CRS={lc.crs().authid()}")
print(f"  Extent: {lc.extent()}")
print(f"  Size: {lc.width()}x{lc.height()}, bands={lc.bandCount()}")
stats_lc = lc.dataProvider().bandStatistics(1)
print(f"  Values: min={stats_lc.minimumValue}, max={stats_lc.maximumValue}, mean={stats_lc.mean:.1f}")

# Road
road = QgsVectorLayer(f"{DATA}\\Road_A.gpkg", "Road_A", "ogr")
print(f"\nRoad: valid={road.isValid()}, CRS={road.crs().authid()}")
print(f"  Features: {road.featureCount()}")
print(f"  Fields: {[(f.name(), f.typeName()) for f in road.fields()]}")
for feat in road.getFeatures():
    geom = feat.geometry()
    print(f"  Road geometry: type={geom.type()}, length_m={geom.length():.1f}")
    print(f"  Attributes: {feat.attributes()}")
    print(f"  Extent: {geom.boundingBox()}")
    break

print(f"\nCRS details:")
from qgis.core import QgsCoordinateReferenceSystem
crs = dem.crs()
print(f"  Description: {crs.description()}")
print(f"  Is geographic: {crs.isGeographic()}")
print(f"  Units: {crs.mapUnits()}")
if crs.isGeographic():
    print("  WARNING: Data is in degrees - need to reproject to metric CRS!")
    # Approximate UTM zone based on extent center
    lon = dem.extent().center().x()
    lat = dem.extent().center().y()
    zone = int((lon + 180) / 6) + 1
    if lat >= 0:
        epsg = f"EPSG:326{zone:02d}"
    else:
        epsg = f"EPSG:327{zone:02d}"
    print(f"  Suggested UTM: {epsg} (zone={zone}, {'N' if lat>=0 else 'S'})")

# Check road CRS vs DEM CRS
print(f"\nCRS consistency: DEM={dem.crs().authid()}, Road={road.crs().authid()}, LC={lc.crs().authid()}")
