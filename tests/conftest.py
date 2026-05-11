"""Test fixtures and configuration for qgis-mcp tests."""

import json
import os
import sys
from pathlib import Path
import pytest

# Ensure the source is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

TEST_DATA_DIR = Path(__file__).parent / "data"
TRAINING_DATA_DIR = Path(__file__).parent.parent / "test_data" / "training" / "QGIS-Training-Data-release_3.44" / "exercise_data"


@pytest.fixture(scope="session")
def test_data_path() -> Path:
    """Return path to synthetic test data directory."""
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return TEST_DATA_DIR


@pytest.fixture(scope="session")
def training_data_path() -> Path:
    """Return path to QGIS training data directory."""
    return TRAINING_DATA_DIR


@pytest.fixture(scope="session")
def mcp_server():
    """Create a FastMCP server instance (no QGIS)."""
    from qgis_mcp.server import create_server
    return create_server()


@pytest.fixture(scope="session")
def registered_tools(mcp_server):
    """Return dict of registered tool names to tool objects."""
    return {name: tool for name, tool in mcp_server._tool_manager._tools.items()}


@pytest.fixture(scope="session")
def registered_resources(mcp_server):
    """Return dict of registered resources."""
    return mcp_server._resource_manager._resources


@pytest.fixture(scope="session")
def registered_prompts(mcp_server):
    """Return dict of registered prompts."""
    return mcp_server._prompt_manager._prompts


def create_synthetic_test_data(data_dir: Path) -> dict:
    """Create synthetic GeoJSON test files for testing without QGIS.

    Returns dict mapping filename -> GeoJSON content.
    """
    data = {}

    # ---- Synthetic buildings (polygons) ----
    buildings = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "House A", "type": "residential", "rooms": 5},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[20.0, -34.0], [20.001, -34.0], [20.001, -34.001], [20.0, -34.001], [20.0, -34.0]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "House B", "type": "residential", "rooms": 3},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[20.002, -34.0], [20.003, -34.0], [20.003, -34.001], [20.002, -34.001], [20.002, -34.0]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "School Building", "type": "education", "rooms": 12},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[20.005, -34.002], [20.007, -34.002], [20.007, -34.004], [20.005, -34.004], [20.005, -34.002]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Restaurant", "type": "commercial", "rooms": 2},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[20.003, -34.005], [20.004, -34.005], [20.004, -34.006], [20.003, -34.006], [20.003, -34.005]]]
                }
            },
        ]
    }
    data["buildings.geojson"] = buildings

    # ---- Synthetic roads (lines) ----
    roads = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Main Road", "highway": "primary", "lanes": 2},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[19.999, -34.0005], [20.004, -34.0005], [20.008, -34.003]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Side Street", "highway": "residential", "lanes": 1},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[20.0025, -34.002], [20.0025, -34.006]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Footpath", "highway": "footway", "lanes": 0},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[20.001, -34.003], [20.003, -34.004]]
                }
            },
        ]
    }
    data["roads.geojson"] = roads

    # ---- Synthetic points (schools, restaurants) ----
    points = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Primary School", "amenity": "school", "capacity": 500},
                "geometry": {"type": "Point", "coordinates": [20.006, -34.003]}
            },
            {
                "type": "Feature",
                "properties": {"name": "Town Restaurant", "amenity": "restaurant", "cuisine": "local"},
                "geometry": {"type": "Point", "coordinates": [20.0035, -34.0055]}
            },
        ]
    }
    data["points_of_interest.geojson"] = points

    # Write all files
    for filename, content in data.items():
        filepath = data_dir / filename
        with open(filepath, "w") as f:
            json.dump(content, f, indent=2)

    return data


@pytest.fixture(scope="session")
def synthetic_data(test_data_path):
    """Create and return synthetic test data."""
    return create_synthetic_test_data(test_data_path)
