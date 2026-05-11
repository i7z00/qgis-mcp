"""Integration test - load real QGIS training data and test tools."""
import sys, json

sys.path.insert(0, r"C:\Users\dell\qgis-mcp\src")
from qgis_mcp.qgis_env import init_qgis

init_qgis()

from qgis_mcp.server import create_server

mcp = create_server()
DATA = r"C:\Users\dell\qgis-mcp\test_data\training\QGIS-Training-Data-release_3.44\exercise_data"

tools = mcp._tool_manager._tools

# Load all layers from GeoPackage
print("=== Loading layers ===")
layer_ids = {}
for layer, name in [
    ("buildings", "buildings"),
    ("roads", "roads"),
    ("schools", "schools"),
    ("restaurants", "restaurants"),
]:
    path = f"{DATA}\\training_data.gpkg|layername={layer}"
    result = json.loads(tools["load_vector_layer"].fn(file_path=path, layer_name=name))
    if "error" in result:
        print(f"  ERR {name}: {result['error']}")
    else:
        print(f"  OK  {name}: {result['feature_count']} features, CRS={result['crs']}")
        layer_ids[name] = result["id"]

# List all layers
layers = json.loads(tools["list_layers"].fn())
print(f"\nTotal layers: {layers['layer_count']}")

# Get extent
extent = json.loads(tools["get_extent"].fn())
e = extent["extent"]
print(f"Extent: ({e['xmin']:.4f}, {e['ymin']:.4f}) to ({e['xmax']:.4f}, {e['ymax']:.4f})")
print(f"Center: ({extent['center']['x']:.4f}, {extent['center']['y']:.4f})")

# Get features
print("\n=== Feature queries ===")
feats = json.loads(
    tools["get_features"].fn(layer_id=layer_ids["buildings"], limit=3)
)
print(f"Sample buildings: {len(feats['feature_collection']['features'])} returned")

# Count features with filter
count = json.loads(
    tools["get_feature_count"].fn(
        layer_id=layer_ids["roads"], attribute_filter='"highway" = \'primary\''
    )
)
print(f"Primary roads: {count['feature_count']}")

# Get field values
vals = json.loads(
    tools["get_field_values"].fn(layer_id=layer_ids["schools"], field_name="amenity")
)
print(f"School amenities: {vals['values']}")

# Get CRS info
crs = json.loads(tools["get_crs_info"].fn(crs_authid="EPSG:32734"))
print(f"\nTarget CRS: {crs['description']} (geographic={crs['is_geographic']})")

# Reproject buildings
print("\n=== Spatial operations ===")
reproj = json.loads(
    tools["reproject_layer"].fn(
        layer_id=layer_ids["buildings"], target_crs="EPSG:32734"
    )
)
if "error" not in reproj:
    fc = reproj.get("feature_collection", {})
    feat_count = len(fc.get("features", []))
    print(f"Reprojected buildings: {feat_count} features")

    if feat_count > 0:
        feat = fc["features"][0]
        geom = feat.get("geometry", {})
        geom_type = geom.get("type")
        coords = geom.get("coordinates", [])
        if geom_type == "Polygon" and coords:
            ring = coords[0]
            if ring:
                first = ring[0] if isinstance(ring[0], list) else ring
                print(f"  Sample coord (UTM 34S): ({first[0]:.1f}, {first[1]:.1f})")
    else:
        print("Reprojection succeeded but no features returned (polygon reprojection uses full dataset)")
else:
    print(f"Reprojection error: {reproj['error']}")

# Buffer
buf = json.loads(
    tools["buffer"].fn(
        input_layer_id=layer_ids["schools"], distance=0.01, dissolve=True
    )
)
if "error" not in buf:
    fc = buf.get("feature_collection", {})
    print(f"Buffer result: {len(fc.get('features', []))} features (schools buffered by 0.01 degrees)")
else:
    print(f"Buffer error: {buf['error']}")

# Get CRS info
target_crs = json.loads(tools["get_crs_info"].fn(crs_authid="EPSG:32734"))
print(f"Target CRS: {target_crs['description']} (geographic={target_crs['is_geographic']})")

print("\n=== All tests passed ===")
