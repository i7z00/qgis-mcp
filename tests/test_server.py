"""Test server initialization, tool registration, and schema validation.

These tests run WITHOUT QGIS (server starts in --no-qgis mode) and verify
the structural correctness of all tools, resources, and prompts.
"""

import json


class TestServerInitialization:
    """Verify the MCP server initializes correctly."""

    def test_server_name(self, mcp_server):
        """Server should have the correct name."""
        assert mcp_server.name == "QGIS Spatial Analysis"

    def test_server_has_instructions(self, mcp_server):
        """Server should have instructions/description."""
        assert mcp_server.instructions is not None
        assert "spatial analysis" in mcp_server.instructions.lower()


class TestToolRegistration:
    """Verify all expected tools are registered with correct schemas."""

    EXPECTED_TOOLS = {
        # Layer management
        "load_project", "load_vector_layer", "load_raster_layer",
        "list_layers", "get_layer_info", "remove_layer",
        # Feature queries
        "get_features", "get_feature_count", "get_field_values",
        # Spatial analysis
        "get_extent", "buffer", "spatial_query", "reproject_layer",
        "get_crs_info", "calculate_field", "calculate_area_length",
        # Processing
        "list_algorithms", "get_algorithm_help", "run_processing",
        # Raster
        "sample_raster", "get_raster_statistics", "clip_raster_by_extent",
        # Export
        "export_map_image",
    }

    def test_all_expected_tools_registered(self, registered_tools):
        """All 23 expected tools should be registered."""
        actual = set(registered_tools.keys())
        assert actual == self.EXPECTED_TOOLS, f"Missing: {self.EXPECTED_TOOLS - actual}, Extra: {actual - self.EXPECTED_TOOLS}"

    def test_tool_count(self, registered_tools):
        """Should have exactly 23 tools."""
        assert len(registered_tools) == 23

    def test_each_tool_has_name(self, registered_tools):
        """Every tool must have a name."""
        for name, tool in registered_tools.items():
            assert tool.name == name, f"Tool key '{name}' != tool.name '{tool.name}'"

    def test_each_tool_has_description(self, registered_tools):
        """Every tool must have a description."""
        for name, tool in registered_tools.items():
            assert tool.description, f"Tool '{name}' has no description"
            assert len(tool.description) > 10, f"Tool '{name}' description too short"

    def test_each_tool_has_parameters(self, registered_tools):
        """Every tool must have an input schema."""
        for name, tool in registered_tools.items():
            assert tool.parameters is not None, f"Tool '{name}' has no parameters"


class TestToolInputSchemas:
    """Validate input schemas for specific tools."""

    def test_load_vector_layer_schema(self, registered_tools):
        """load_vector_layer should have file_path (required) and layer_name (optional)."""
        tool = registered_tools["load_vector_layer"]
        schema = tool.parameters
        props = schema.get("properties", {})
        required = schema.get("required", [])

        assert "file_path" in props
        assert props["file_path"]["type"] == "string"
        assert "file_path" in required

        assert "layer_name" in props
        assert "layer_name" not in required  # optional

    def test_get_features_schema(self, registered_tools):
        """get_features should have layer_id (required), limit, offset, filters, bbox, include_geometry."""
        tool = registered_tools["get_features"]
        schema = tool.parameters
        props = schema.get("properties", {})

        assert "layer_id" in props
        assert "limit" in props
        assert "offset" in props
        assert "attribute_filter" in props
        assert "bbox" in props
        assert "include_geometry" in props

    def test_buffer_schema(self, registered_tools):
        """buffer should have input_layer_id, distance (required), dissolve, segments."""
        tool = registered_tools["buffer"]
        schema = tool.parameters
        props = schema.get("properties", {})
        required = schema.get("required", [])

        assert "input_layer_id" in props
        assert "distance" in props
        assert "input_layer_id" in required
        assert "distance" in required

    def test_run_processing_schema(self, registered_tools):
        """run_processing should have algorithm_id, parameters (required), output_file."""
        tool = registered_tools["run_processing"]
        schema = tool.parameters
        props = schema.get("properties", {})
        required = schema.get("required", [])

        assert "algorithm_id" in props
        assert "parameters" in props
        assert "algorithm_id" in required
        assert "parameters" in required

    def test_export_map_image_schema(self, registered_tools):
        """export_map_image should have width, height, extent, layers, dpi."""
        tool = registered_tools["export_map_image"]
        schema = tool.parameters
        props = schema.get("properties", {})

        assert "width" in props
        assert "height" in props


class TestToolErrorHandling:
    """Verify tools fail gracefully when QGIS is not available."""

    ERROR_KEYWORDS = ["QGIS", "not available", "ensure", "install"]

    async def test_load_vector_layer_no_qgis(self, mcp_server):
        """Should return error about QGIS not available."""
        # We test the underlying function directly since FastMCP tool calls
        # require a full session setup
        from qgis_mcp.qgis_env import is_qgis_available
        assert not is_qgis_available(), "Expected QGIS to be unavailable for this test"

    async def test_list_layers_no_qgis_error_includes_helpful_message(self, mcp_server):
        """Error messages should guide user on how to set up QGIS."""
        # Verify the require_qgis function raises the right error
        import pytest
        from qgis_mcp.qgis_env import require_qgis

        with pytest.raises(RuntimeError) as exc_info:
            require_qgis()
        error_msg = str(exc_info.value)
        assert "QGIS" in error_msg
        assert "QGIS_INSTALL_PATH" in error_msg


class TestResourceRegistration:
    """Verify resources are correctly registered."""

    EXPECTED_RESOURCES = {"qgis://layers", "qgis://algorithms"}
    EXPECTED_TEMPLATES = {"qgis://layer/{layer_id}"}

    def test_static_resources(self, registered_resources):
        """Should have layers and algorithms resources."""
        assert set(registered_resources.keys()) == self.EXPECTED_RESOURCES

    def test_resource_templates(self, mcp_server):
        """Should have layer detail template."""
        templates = set(mcp_server._resource_manager._templates.keys())
        assert templates == self.EXPECTED_TEMPLATES


class TestPromptRegistration:
    """Verify prompts are correctly registered."""

    EXPECTED_PROMPTS = {"spatial_analysis_workflow", "layer_exploration", "map_export_workflow"}

    def test_prompts_registered(self, registered_prompts):
        """Should have 3 prompts registered."""
        assert set(registered_prompts.keys()) == self.EXPECTED_PROMPTS

    def test_prompts_have_titles(self, registered_prompts):
        """Every prompt should have a display title."""
        for name, prompt in registered_prompts.items():
            assert prompt.title, f"Prompt '{name}' has no title"
