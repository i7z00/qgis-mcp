"""
Evaluation harness for testing the QGIS MCP server with the Swellendam
vector analysis tutorial (QGIS Training Manual, Section 6.2).

Test Scenario: Find residential properties matching 5 criteria:
1. Located in Swellendam
2. Within 1km of a school
3. More than 100m² in size
4. Closer than 50m to a main road
5. Closer than 500m to a restaurant

This module defines the expected workflow and validates AI model output
against known correct answers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
import json
from pathlib import Path


class StepStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class StepResult:
    """Result of a single workflow step."""
    step: str
    status: StepStatus
    tool_used: str | None = None
    expected: Any | None = None
    actual: Any | None = None
    error: str | None = None
    notes: str = ""


@dataclass
class ScenarioResult:
    """Complete result of a test scenario execution."""
    scenario_name: str
    steps: list[StepResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0

    def add(self, result: StepResult) -> None:
        self.steps.append(result)
        if result.status == StepStatus.PASS:
            self.passed += 1
        elif result.status in (StepStatus.FAIL, StepStatus.ERROR):
            self.failed += 1

    def summary(self) -> str:
        lines = [
            f"\n{'='*60}",
            f"Scenario: {self.scenario_name}",
            f"Results: {self.passed} passed, {self.failed} failed, {len(self.steps)} total",
            f"{'='*60}",
        ]
        for s in self.steps:
            icon = {"pass": "[PASS]", "fail": "[FAIL]", "skip": "[SKIP]", "error": "[ERR ]"}[s.status.value]
            lines.append(f"  {icon} {s.step}")
            if s.notes:
                lines.append(f"       {s.notes}")
            if s.error:
                lines.append(f"       Error: {s.error}")
        return "\n".join(lines)


# ─── Scenario 1: Vector Analysis (Swellendam Property Search) ───

SCENARIO_VECTOR_ANALYSIS = {
    "name": "Swellendam Property Search (Training Manual 6.2)",
    "description": """
Find residential properties in Swellendam meeting all criteria:
1. Within 1km of a school
2. More than 100m² in size
3. Closer than 50m to a main road
4. Closer than 500m to a restaurant
""",
    "data_sources": {
        "training_data.gpkg": "GeoPackage with buildings, roads, restaurants, schools layers",
        "landuse.sqlite": "SpatiaLite with land use polygons",
    },
    "crs": "EPSG:32734",  # WGS 84 / UTM zone 34S
    "workflow": [
        {
            "step": "Load project data",
            "tool": "load_vector_layer",
            "params": {"file_path": "{data_dir}/training_data.gpkg|layername=buildings", "layer_name": "buildings"},
            "assert": "layer_is_valid",
        },
        {
            "step": "Load roads layer",
            "tool": "load_vector_layer",
            "params": {"file_path": "{data_dir}/training_data.gpkg|layername=roads", "layer_name": "roads"},
            "assert": "layer_is_valid",
        },
        {
            "step": "Load restaurants layer",
            "tool": "load_vector_layer",
            "params": {"file_path": "{data_dir}/training_data.gpkg|layername=restaurants", "layer_name": "restaurants"},
            "assert": "layer_is_valid",
        },
        {
            "step": "Load schools layer",
            "tool": "load_vector_layer",
            "params": {"file_path": "{data_dir}/training_data.gpkg|layername=schools", "layer_name": "schools"},
            "assert": "layer_is_valid",
        },
        {
            "step": "Verify layers loaded",
            "tool": "list_layers",
            "params": {},
            "assert": "layer_count >= 4",
        },
        {
            "step": "Get buildings layer info",
            "tool": "get_layer_info",
            "params": {"layer_id": "{buildings_id}"},
            "assert": "has_feature_count",
        },
        {
            "step": "Reproject buildings to UTM 34S",
            "tool": "reproject_layer",
            "params": {"layer_id": "{buildings_id}", "target_crs": "EPSG:32734"},
            "assert": "has_features",
        },
        {
            "step": "Buffer roads by 50m",
            "tool": "buffer",
            "params": {"input_layer_id": "{roads_id}", "distance": 50, "dissolve": True},
            "assert": "has_features",
        },
        {
            "step": "Buffer schools by 1000m",
            "tool": "buffer",
            "params": {"input_layer_id": "{schools_id}", "distance": 1000, "dissolve": True},
            "assert": "has_features",
        },
        {
            "step": "Intersect road and school buffers",
            "tool": "run_processing",
            "params": {
                "algorithm_id": "native:intersection",
                "parameters": json.dumps({
                    "INPUT": "{roads_buffer_layer_id}",
                    "OVERLAY": "{schools_buffer_layer_id}",
                })
            },
            "assert": "has_output",
        },
        {
            "step": "Extract buildings in intersection area",
            "tool": "spatial_query",
            "params": {
                "source_layer_id": "{buildings_reprojected_id}",
                "reference_layer_id": "{intersection_layer_id}",
                "predicate": "intersects",
            },
            "assert": "has_features",
        },
        {
            "step": "Buffer restaurants by 500m",
            "tool": "buffer",
            "params": {"input_layer_id": "{restaurants_id}", "distance": 500, "dissolve": True},
            "assert": "has_features",
        },
        {
            "step": "Further filter by restaurant proximity",
            "tool": "spatial_query",
            "params": {
                "source_layer_id": "{buildings_intersect_id}",
                "reference_layer_id": "{restaurants_buffer_id}",
                "predicate": "intersects",
            },
            "assert": "has_features",
        },
        {
            "step": "Calculate building areas",
            "tool": "calculate_area_length",
            "params": {"layer_id": "{filtered_buildings_id}"},
            "assert": "has_area_stats",
        },
        {
            "step": "Export map of results",
            "tool": "export_map_image",
            "params": {"layers": "{filtered_buildings_id}", "width": 1200, "height": 900},
            "assert": "output_file_exists",
        },
    ],
    "expected_outputs": {
        "final_feature_count_min": 1,
        "final_feature_count_max": 100,
        "all_buildings_meet_criteria": True,
    },
}


# ─── Scenario 2: Basic Layer Operations ───

SCENARIO_BASIC_OPS = {
    "name": "Basic Layer Operations",
    "description": "Load, inspect, and query spatial data from synthetic GeoJSON files.",
    "data_sources": {
        "buildings.geojson": "Synthetic building polygons",
        "roads.geojson": "Synthetic road lines",
        "points_of_interest.geojson": "Synthetic point features",
    },
    "crs": "EPSG:4326",
    "workflow": [
        {
            "step": "Load buildings from GeoJSON",
            "tool": "load_vector_layer",
            "params": {"file_path": "{data_dir}/buildings.geojson", "layer_name": "buildings"},
            "assert": "layer_is_valid",
        },
        {
            "step": "Load roads from GeoJSON",
            "tool": "load_vector_layer",
            "params": {"file_path": "{data_dir}/roads.geojson", "layer_name": "roads"},
            "assert": "layer_is_valid",
        },
        {
            "step": "Load points of interest from GeoJSON",
            "tool": "load_vector_layer",
            "params": {"file_path": "{data_dir}/points_of_interest.geojson", "layer_name": "pois"},
            "assert": "layer_is_valid",
        },
        {
            "step": "List all layers",
            "tool": "list_layers",
            "params": {},
            "assert": "layer_count == 3",
        },
        {
            "step": "Get building layer info",
            "tool": "get_layer_info",
            "params": {"layer_id": "{buildings_id}"},
            "assert": "feature_count == 4",
        },
        {
            "step": "Get features from buildings",
            "tool": "get_features",
            "params": {"layer_id": "{buildings_id}", "limit": 10},
            "assert": "returned >= 4",
        },
        {
            "step": "Filter buildings by type",
            "tool": "get_features",
            "params": {"layer_id": "{buildings_id}", "attribute_filter": '"type" = \'residential\''},
            "assert": "returned >= 2",
        },
        {
            "step": "Get unique building types",
            "tool": "get_field_values",
            "params": {"layer_id": "{buildings_id}", "field_name": "type", "distinct": True},
            "assert": "values_contain 'residential'",
        },
        {
            "step": "Get feature count",
            "tool": "get_feature_count",
            "params": {"layer_id": "{buildings_id}"},
            "assert": "feature_count == 4",
        },
        {
            "step": "Get extent of all layers",
            "tool": "get_extent",
            "params": {},
            "assert": "has_extent_keys",
        },
        {
            "step": "Get CRS info for EPSG:4326",
            "tool": "get_crs_info",
            "params": {"crs_authid": "EPSG:4326"},
            "assert": "is_geographic == True",
        },
    ],
    "expected_outputs": {
        "buildings_count": 4,
        "roads_count": 3,
        "pois_count": 2,
    },
}


# ─── Scenario 3: Processing Algorithm Tool Tests ───

SCENARIO_PROCESSING = {
    "name": "Processing Algorithm Discovery",
    "description": "Test the processing tool listing and help functions.",
    "workflow": [
        {
            "step": "List all algorithms",
            "tool": "list_algorithms",
            "params": {},
            "assert": "total_available > 0",
        },
        {
            "step": "Filter algorithms by 'buffer'",
            "tool": "list_algorithms",
            "params": {"filter_text": "buffer"},
            "assert": "returned > 0",
        },
        {
            "step": "Get buffer algorithm help",
            "tool": "get_algorithm_help",
            "params": {"algorithm_id": "native:buffer"},
            "assert": "has_parameters",
        },
        {
            "step": "Get intersection algorithm help",
            "tool": "get_algorithm_help",
            "params": {"algorithm_id": "native:intersection"},
            "assert": "has_parameters",
        },
        {
            "step": "Filter algorithms by 'clip'",
            "tool": "list_algorithms",
            "params": {"filter_text": "clip"},
            "assert": "returned > 0",
        },
    ],
}


ALL_SCENARIOS = [SCENARIO_VECTOR_ANALYSIS, SCENARIO_BASIC_OPS, SCENARIO_PROCESSING]
