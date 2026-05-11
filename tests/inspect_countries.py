"""Quick inspection of Natural Earth countries layer."""
from qgis.core import QgsVectorLayer

NE = r"C:\Users\dell\qgis-mcp\test_data\naturalearth"
countries = QgsVectorLayer(f"{NE}\\countries\\ne_10m_admin_0_countries.shp", "countries", "ogr")
print("Countries:", countries.featureCount(), "features")
print("CRS:", countries.crs().authid())
print("Fields:", [(f.name(), f.typeName()) for f in countries.fields()])

for f in countries.getFeatures():
    name = f.attribute("ADMIN") or ""
    if "France" in name or "france" in name.lower():
        print(f"\nFrance: ADMIN={f.attribute('ADMIN')}")
        print(f"  SOVEREIGNT={f.attribute('SOVEREIGNT')}")
        print(f"  NAME={f.attribute('NAME')}")
        print(f"  FORMAL_EN={f.attribute('FORMAL_EN')}")
        print(f"  ISO_A2={f.attribute('ISO_A2')}")
        geom = f.geometry()
        print(f"  Geometry: {geom.type()}, area_deg={geom.area():.4f}")
        break
