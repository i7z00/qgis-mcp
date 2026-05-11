"""
Natural Earth Highway Buffer Analysis for France

Uses file-based outputs for reliable inter-step layer passing.
"""

import sys, json, tempfile
from pathlib import Path

sys.path.insert(0, r"C:\Users\dell\qgis-mcp\src")
from qgis_mcp.qgis_env import init_qgis

init_qgis()
from qgis_mcp.server import create_server

mcp = create_server()
tools = mcp._tool_manager._tools
NE = r"C:\Users\dell\qgis-mcp\test_data\naturalearth"
TMP = Path(tempfile.gettempdir())

# ─── Step 1: Load layers ───
print("=" * 60)
print("Step 1: Loading layers")
print("=" * 60)

r = json.loads(tools["load_vector_layer"].fn(file_path=f"{NE}\\countries\\ne_10m_admin_0_countries.shp", layer_name="countries"))
print(f"  Countries: {r['feature_count']} features, CRS={r['crs']}")
countries_id = r["id"]

r = json.loads(tools["load_vector_layer"].fn(file_path=f"{NE}\\roads\\ne_10m_roads.shp", layer_name="roads"))
print(f"  Roads: {r['feature_count']} features")
roads_id = r["id"]

# ─── Step 2: Extract Major Highways to file ───
print("\nStep 2: Extract Major Highways to file")
highways_path = str(TMP / "major_highways.gpkg")
r = json.loads(tools["run_processing"].fn(
    algorithm_id="native:extractbyexpression",
    parameters=json.dumps({
        "INPUT": roads_id,
        "EXPRESSION": '"type" = \'Major Highway\'',
        "OUTPUT": highways_path
    })
))
if "error" in r:
    print(f"  ERROR: {r['error']}"); sys.exit(1)
print(f"  Saved to: {highways_path}")

# Load the saved highways file
r = json.loads(tools["load_vector_layer"].fn(file_path=highways_path, layer_name="major_highways"))
highways_id = r["id"]
print(f"  Loaded: {r['feature_count']} features, id={highways_id[:20]}...")

# ─── Step 3: Reproject to EPSG:3857 ───
print("\nStep 3: Reproject to EPSG:3857")
reproj_path = str(TMP / "major_highways_3857.gpkg")
r = json.loads(tools["run_processing"].fn(
    algorithm_id="native:reprojectlayer",
    parameters=json.dumps({
        "INPUT": highways_id,
        "TARGET_CRS": "EPSG:3857",
        "OUTPUT": reproj_path
    })
))
if "error" in r:
    print(f"  ERROR: {r['error']}"); sys.exit(1)
print(f"  Saved to: {reproj_path}")

r = json.loads(tools["load_vector_layer"].fn(file_path=reproj_path, layer_name="highways_3857"))
highways_3857_id = r["id"]
print(f"  Loaded: {r['feature_count']} features (EPSG:3857)")

# ─── Step 4: Buffer 10km ───
print("\nStep 4: Buffer 10km (dissolved)")
buffer_path = str(TMP / "highway_buffer_10km.gpkg")
r = json.loads(tools["run_processing"].fn(
    algorithm_id="native:buffer",
    parameters=json.dumps({
        "INPUT": highways_3857_id,
        "DISTANCE": 10000,
        "DISSOLVE": True,
        "OUTPUT": buffer_path
    })
))
if "error" in r:
    print(f"  ERROR: {r['error']}"); sys.exit(1)
print(f"  Saved to: {buffer_path}")

r = json.loads(tools["load_vector_layer"].fn(file_path=buffer_path, layer_name="highway_buffer_10km"))
buffer_id = r["id"]
print(f"  Loaded buffer: {r['feature_count']} features")

# ─── Step 5: Extract France ───
print("\nStep 5: Extract France")
france_path = str(TMP / "france.gpkg")
r = json.loads(tools["run_processing"].fn(
    algorithm_id="native:extractbyexpression",
    parameters=json.dumps({
        "INPUT": countries_id,
        "EXPRESSION": '"ADMIN" = \'France\'',
        "OUTPUT": france_path
    })
))
if "error" in r:
    print(f"  ERROR: {r['error']}"); sys.exit(1)

r = json.loads(tools["load_vector_layer"].fn(file_path=france_path, layer_name="france"))
france_id = r["id"]
print(f"  Loaded France: {r['feature_count']} features")

# ─── Step 6: Intersect buffer with France ───
print("\nStep 6: Intersect buffer with France")
intersect_path = str(TMP / "buffer_france_intersect.gpkg")
r = json.loads(tools["run_processing"].fn(
    algorithm_id="native:intersection",
    parameters=json.dumps({
        "INPUT": buffer_id,
        "OVERLAY": france_id,
        "OUTPUT": intersect_path
    })
))
if "error" in r:
    print(f"  ERROR: {r['error']}"); sys.exit(1)

r = json.loads(tools["load_vector_layer"].fn(file_path=intersect_path, layer_name="buffer_in_france"))
intersect_id = r["id"]
print(f"  Intersection: {r['feature_count']} features")

# ─── Step 7: Calculate area ───
print("\nStep 7: Calculate total area")
area_result = json.loads(tools["calculate_area_length"].fn(layer_id=intersect_id))
print(f"  Raw area result: {area_result}")

if "area" in area_result:
    area_m2 = area_result["area"]["sum"]
    area_km2 = area_m2 / 1_000_000
    print(f"\n{'='*60}")
    print(f"  RESULT: Total highway buffer area in France: {area_km2:,.1f} km²")
    print(f"          ({area_m2:,.0f} m²)")
    print(f"{'='*60}")
elif "length" in area_result:
    length = area_result["length"]["sum"] / 1000
    print(f"  Got length instead: {length:,.1f} km (intersection produced lines)")
else:
    print(f"  Unexpected result: {area_result}")
