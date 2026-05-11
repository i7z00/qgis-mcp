"""Processing algorithm tools - run QGIS processing algorithms."""

import json

from ..qgis_env import require_qgis


def register_tools(mcp):
    """Register processing algorithm tools on the FastMCP instance."""

    @mcp.tool()
    def list_algorithms(filter_text: str = "", max_results: int = 50) -> str:
        """
        List available QGIS processing algorithms.

        Args:
            filter_text: Optional filter string to search algorithm names/IDs.
            max_results: Maximum number of results to return (default 50).
        """
        require_qgis()
        from qgis.core import QgsApplication

        registry = QgsApplication.processingRegistry()
        all_algs = registry.algorithms()

        results = []
        filter_lower = filter_text.lower()

        for alg in all_algs:
            name = alg.displayName()
            alg_id = alg.id()
            if filter_lower:
                if filter_lower not in name.lower() and filter_lower not in alg_id.lower():
                    continue

            results.append({
                "id": alg_id,
                "name": name,
                "provider": alg.provider().name() if alg.provider() else "unknown",
            })

            if len(results) >= max_results:
                break

        return json.dumps({
            "total_available": len(all_algs),
            "returned": len(results),
            "filter": filter_text or None,
            "algorithms": results,
        })

    @mcp.tool()
    def get_algorithm_help(algorithm_id: str) -> str:
        """
        Get detailed parameter information for a processing algorithm.

        Args:
            algorithm_id: The algorithm ID (e.g. 'native:buffer', 'gdal:cliprasterbyextent').
        """
        require_qgis()
        from qgis.core import QgsApplication

        registry = QgsApplication.processingRegistry()
        alg = registry.algorithmById(algorithm_id)

        if alg is None:
            return json.dumps({
                "error": f"Algorithm not found: {algorithm_id}",
                "hint": "Use list_algorithms to find available algorithms.",
            })

        params = []
        for p in alg.parameterDefinitions():
            param_info = {
                "name": p.name(),
                "description": p.description(),
                "type": p.type(),
                "default": str(p.defaultValue()) if p.defaultValue() else None,
                "optional": bool(p.flags() & p.FlagOptional),
            }
            params.append(param_info)

        return json.dumps({
            "id": alg.id(),
            "name": alg.displayName(),
            "short_description": alg.shortDescription() if hasattr(alg, "shortDescription") else "",
            "provider": alg.provider().name() if alg.provider() else "unknown",
            "parameters": params,
        })

    @mcp.tool()
    def run_processing(
        algorithm_id: str,
        parameters: str,
        output_file: str | None = None,
    ) -> str:
        """
        Run a QGIS processing algorithm.

        Args:
            algorithm_id: The algorithm ID (e.g. 'native:buffer', 'gdal:cliprasterbyextent').
            parameters: JSON string of algorithm parameters. Use get_algorithm_help for parameter names.
                        Layer references can use layer IDs from list_layers.
                        Example: '{"INPUT": "layer_id_123", "DISTANCE": 100, "OUTPUT": "memory:"}'
            output_file: Optional output file path. If not provided, uses temporary file and returns GeoJSON (for vectors).
        """
        require_qgis()
        from qgis.core import QgsApplication, QgsProject, QgsJsonExporter
        from qgis import processing
        import tempfile
        from pathlib import Path

        registry = QgsApplication.processingRegistry()
        alg = registry.algorithmById(algorithm_id)
        if alg is None:
            return json.dumps({
                "error": f"Algorithm not found: {algorithm_id}",
                "hint": "Use list_algorithms to find available algorithms.",
            })

        try:
            params = json.loads(parameters)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON parameters: {e}"})

        # Resolve layer IDs to actual QGIS layer objects
        project = QgsProject.instance()
        resolved_params = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("layer_id_"):
                layer = project.mapLayer(value)
                if layer:
                    resolved_params[key] = layer
                else:
                    return json.dumps({"error": f"Layer not found for parameter '{key}': {value}"})
            else:
                resolved_params[key] = value

        try:
            result = processing.run(algorithm_id, resolved_params)

            # Build response - only include serializable output keys
            output_info = {}
            for key, value in result.items():
                if isinstance(value, str):
                    output_info[key] = value
                elif hasattr(value, "id"):
                    output_info[key] = f"layer:{value.id()}"
                else:
                    try:
                        output_info[key] = str(value)
                    except Exception:
                        output_info[key] = "unsupported_output_type"

            return json.dumps({
                "algorithm": algorithm_id,
                "output": output_info,
            })

        except Exception as e:
            return json.dumps({
                "error": f"Algorithm execution failed: {e}",
                "algorithm": algorithm_id,
            })


def _load_temp_layer(path: str):
    """Load a temporary vector layer from path."""
    from qgis.core import QgsVectorLayer
    layer = QgsVectorLayer(path, "temp", "ogr")
    return layer if layer.isValid() else None
