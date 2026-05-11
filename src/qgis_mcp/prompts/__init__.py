"""Prompt templates for spatial analysis workflows."""

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register all prompts on the FastMCP instance."""

    @mcp.prompt(title="Spatial Analysis Workflow")
    def spatial_analysis_workflow(
        goal: str = "Analyze spatial patterns and relationships in the data",
        data_description: str = "A set of vector and raster layers describing the study area",
    ) -> str:
        """
        Generate a prompt for conducting spatial analysis on GIS data.

        Args:
            goal: What you want to achieve with the analysis.
            data_description: Brief description of the data layers available.
        """
        return f"""You are a GIS spatial analysis expert working with QGIS data.

## Goal
{goal}

## Available Data
{data_description}

## Instructions
1. Start by listing the available layers using the list_layers tool
2. For each relevant layer, get detailed information using get_layer_info
3. Examine the extent of the data using get_extent
4. Plan your analysis steps:
   - For vector analysis: use spatial_query, buffer, calculate_area_length, calculate_field
   - For raster analysis: use sample_raster, get_raster_statistics, clip_raster_by_extent
   - For data processing: use run_processing with algorithms from list_algorithms
5. Execute each step using the appropriate tools
6. For spatial queries, remember to:
   - Check CRS compatibility with get_crs_info
   - Use reproject_layer if CRS differs between layers
7. Present findings clearly with numeric results and spatial extents

## Tips
- Use get_algorithm_help to understand processing algorithm parameters before running them
- Start with small feature counts using limit parameter to test queries
- Export map images to visualize results using export_map_image"""

    @mcp.prompt(title="Layer Data Exploration")
    def layer_exploration(
        layer_description: str = "A GIS layer to explore",
    ) -> str:
        """
        Generate a prompt for exploring and understanding a GIS layer.

        Args:
            layer_description: What kind of layer you want to explore.
        """
        return f"""You are exploring GIS data in a QGIS project.

## Layer to Explore
{layer_description}

## Exploration Steps
1. List all layers with list_layers to find the target layer
2. Get detailed layer info with get_layer_info (fields, types, extent, CRS)
3. Get field values with get_field_values to understand data distributions
4. Sample some features with get_features (use limit=10 first)
5. Analyze spatial properties:
   - For polygons: use calculate_area_length for area/perimeter stats
   - For lines: use calculate_area_length for length stats
   - For points: use get_extent to see distribution
6. Summarize your findings:
   - Spatial extent and CRS
   - Attribute fields and their value ranges
   - Feature count and geometry type
   - Any notable patterns or data quality issues"""

    @mcp.prompt(title="Map Layout Export")
    def map_export_workflow(
        purpose: str = "Create a visualization of spatial analysis results",
    ) -> str:
        """
        Generate a prompt for creating map exports.

        Args:
            purpose: The purpose of the map export.
        """
        return f"""You are creating a map export from QGIS spatial data.

## Purpose
{purpose}

## Steps
1. Ensure the necessary layers are loaded (load_vector_layer, load_raster_layer)
2. Check the extent with get_extent to understand the area
3. Optionally style analysis results before export:
   - Use calculate_field to add computed attributes
   - Use buffer or spatial_query to create analysis layers
4. Export the map with export_map_image:
   - Set appropriate width and height
   - Specify extent if you want to zoom to a particular area
   - Control which layers to include with the layers parameter
5. Describe the exported map contents and what it shows"""
