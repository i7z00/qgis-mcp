"""
Test runner that validates tool output against expected assertions.

Works both with and without QGIS installed. When QGIS is not available,
tools are expected to return errors gracefully.
"""

import json
import re
from dataclasses import dataclass
from typing import Any

from .scenarios import (
    ALL_SCENARIOS,
    ScenarioResult,
    StepResult,
    StepStatus,
)


@dataclass
class AssertionResult:
    success: bool
    message: str


def evaluate_assertion(assertion: str, json_output: str) -> AssertionResult:
    """Evaluate a human-readable assertion against JSON tool output.

    Supported assertion formats:
        - "layer_is_valid" - no error key in output
        - "has_features" - has feature_collection or features
        - "has_extent_keys" - has xmin, ymin, xmax, ymax
        - "has_area_stats" - has area key in output
        - "has_output" - result has output field
        - "has_parameters" - has parameters in output
        - "layer_count >= N" - check layer count
        - "layer_count == N" - exactly N layers
        - "feature_count == N" - count equals N
        - "feature_count >= N" - count at least N
        - "returned >= N" - returned at least N
        - "total_available > 0" - total_available is positive
        - "values_contain 'X'" - values list contains X
        - "is_geographic == True/False" - CRS property check
        - "output_file_exists" - output field present
        - "has_feature_count" - feature_count key present
    """
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError:
        return AssertionResult(False, f"Invalid JSON output: {json_output[:100]}")

    # ---- layer_is_valid ----
    if assertion == "layer_is_valid":
        if "error" in data:
            return AssertionResult(False, f"Layer not valid: {data['error']}")
        return AssertionResult(True, "Layer is valid")

    # ---- has_features ----
    if assertion == "has_features":
        if "feature_collection" in data:
            fc = data["feature_collection"]
            count = len(fc.get("features", []))
            return AssertionResult(count > 0, f"Has {count} features")
        if "feature_count" in data and data["feature_count"] > 0:
            return AssertionResult(True, f"Has {data['feature_count']} features")
        return AssertionResult(False, "No features found")

    # ---- has_extent_keys ----
    if assertion == "has_extent_keys":
        if "extent" in data:
            e = data["extent"]
            has_keys = all(k in e for k in ("xmin", "ymin", "xmax", "ymax"))
            return AssertionResult(has_keys, f"Extent keys present: {has_keys}")
        if "layers" in data:
            return AssertionResult(True, "Has layers extent")
        return AssertionResult(False, "No extent info")

    # ---- has_area_stats ----
    if assertion == "has_area_stats":
        has_area = "area" in data
        has_length = "length" in data
        return AssertionResult(has_area or has_length, f"Has area={has_area}, length={has_length}")

    # ---- has_output ----
    if assertion == "has_output":
        has_out = "output" in data
        return AssertionResult(has_out, f"Has output: {has_out}")

    # ---- has_parameters ----
    if assertion == "has_parameters":
        has_params = "parameters" in data
        return AssertionResult(has_params, f"Has parameters: {has_params}")

    # ---- has_feature_count ----
    if assertion == "has_feature_count":
        has_fc = "feature_count" in data
        return AssertionResult(has_fc, f"Has feature_count: {has_fc}")

    # ---- output_file_exists ----
    if assertion == "output_file_exists":
        has_out = "output" in data
        return AssertionResult(has_out, f"Output file present: {has_out}")

    # ---- Numeric comparisons ----
    match = re.match(r"(\w+)\s*(>=|==|>|<=|<)\s*(\d+(\.\d+)?)", assertion)
    if match:
        key = match.group(1)
        op = match.group(2)
        expected = float(match.group(3))

        actual = None
        # Search for the key in the top-level dict
        if key in data:
            actual = data[key]
        else:
            # Try to extract from 'result' key or nested
            for k, v in data.items():
                if k == key:
                    actual = v
                    break

        if actual is None:
            return AssertionResult(False, f"Key '{key}' not found in output")

        try:
            actual_num = float(actual) if isinstance(actual, (int, float)) else len(actual) if isinstance(actual, list) else actual
        except (TypeError, ValueError):
            return AssertionResult(False, f"Cannot compare {key}={actual} ({type(actual).__name__})")

        if op == ">=":
            ok = actual_num >= expected
        elif op == "==":
            ok = actual_num == expected
        elif op == ">":
            ok = actual_num > expected
        elif op == "<=":
            ok = actual_num <= expected
        elif op == "<":
            ok = actual_num < expected
        else:
            return AssertionResult(False, f"Unknown operator: {op}")

        return AssertionResult(ok, f"{key} {op} {expected}: actual={actual_num} ({'OK' if ok else 'FAIL'})")

    # ---- values_contain 'X' ----
    match = re.match(r"values_contain\s+'([^']+)'", assertion)
    if match:
        needle = match.group(1)
        values = data.get("values", [])
        contains = any(needle in str(v) for v in values)
        return AssertionResult(contains, f"Values contain '{needle}': {contains}")

    # ---- is_geographic == True/False ----
    match = re.match(r"is_geographic\s*==\s*(True|False)", assertion)
    if match:
        expected_bool = match.group(1) == "True"
        actual_bool = data.get("is_geographic", None)
        ok = actual_bool == expected_bool
        return AssertionResult(ok, f"is_geographic == {expected_bool}: actual={actual_bool} ({'OK' if ok else 'FAIL'})")

    return AssertionResult(False, f"Unknown assertion format: {assertion}")


def run_scenario_schema_only(scenario: dict) -> ScenarioResult:
    """Run a scenario checking only that tools exist with correct schemas.

    This works without QGIS - validates tool structure only.
    """
    from qgis_mcp.server import create_server

    server = create_server()
    tools = {name: tool for name, tool in server._tool_manager._tools.items()}

    result = ScenarioResult(scenario["name"])

    for step_def in scenario.get("workflow", []):
        tool_name = step_def["tool"]

        step_result = StepResult(
            step=step_def["step"],
            status=StepStatus.SKIP,
            tool_used=tool_name,
        )

        if tool_name not in tools:
            step_result.status = StepStatus.FAIL
            step_result.error = f"Tool '{tool_name}' not registered"
        else:
            tool = tools[tool_name]
            # Validate input schema matches
            params = step_def.get("params", {})
            schema_props = tool.parameters.get("properties", {})
            missing_params = set(params.keys()) - set(schema_props.keys())
            if missing_params and not any("{" in v for v in params.values()):
                step_result.status = StepStatus.FAIL
                step_result.error = f"Parameters not in schema: {missing_params}"
            else:
                step_result.status = StepStatus.PASS
                step_result.notes = f"Tool '{tool_name}' exists with correct schema"

        result.add(step_result)

    return result


def run_all_scenarios() -> list[ScenarioResult]:
    """Run all defined scenarios (schema validation only when no QGIS)."""
    results = []
    for scenario in ALL_SCENARIOS:
        result = run_scenario_schema_only(scenario)
        results.append(result)
    return results
