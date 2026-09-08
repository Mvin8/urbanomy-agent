from .data import ScenarioRegistry, target_row
from .jobs import JobManager
from .schemas import DERIVED, INDEPENDENT, LAND_USES, EstimateRequest, OptimizationRequest


class UrbanomyService:
    def __init__(self, settings, jobs=None):
        self.settings = settings
        self.registry = ScenarioRegistry(settings.data_dir)
        self.jobs = jobs if jobs is not None else JobManager(settings)

    def list_blocks(self, scenario_id, offset=0, limit=50):
        if not 0 <= offset or not 1 <= limit <= 200:
            raise ValueError("offset >= 0 and 1 <= limit <= 200 are required.")
        import json

        blocks = self.registry.blocks(scenario_id)
        columns = ["id", "site_area", "land_use", "footprint_area", "l"]
        return {"scenario_id": scenario_id, "total": len(blocks), "offset": offset,
                "blocks": json.loads(blocks.iloc[offset:offset + limit][columns].to_json(orient="records"))}

    def options(self, scenario_id, target_id):
        import json

        blocks = self.registry.blocks(scenario_id)
        row = target_row(blocks, target_id)
        geometry = json.loads(blocks.loc[[row.name]].to_crs(4326).to_json())["features"][0]["geometry"]
        return {"scenario_id": scenario_id, "target_id": target_id, "geometry": geometry,
                "baseline": json.loads(row[list(INDEPENDENT + DERIVED)].to_json()),
                "independent_parameters": list(INDEPENDENT), "derived_constraints": list(DERIVED),
                "units": {**{k: "fraction [0,1]" for k in (*LAND_USES, "mxi", "gsi")},
                          **{k: "m²" for k in ("footprint_area", "build_floor_area", "living_area", "non_living_area")},
                          "l": "average floors >= 1 (continuous)", "fsi": "floor area / site area", "population": "people"},
                "footprint_area_max": float(row.site_area) * 0.8,
                "rules": ["Unspecified independent parameters stay at baseline (land-use shares normalized to sum 1).",
                          "Land-use fractions must sum to 1 after optimization.",
                          "Final footprint_area must be positive; l.min >= 1; derived indicators are recalculated.",
                          "The strategy scorer sees scenario parameters, land-value gain and investor NPV only."]}

    def submit(self, operation, payload, owner="mcp"):
        if operation not in ("estimate_land_value", "optimize_district"):
            raise ValueError("Unknown operation.")
        schema = OptimizationRequest if operation == "optimize_district" else EstimateRequest
        request = schema.model_validate(payload)
        self.registry.paths(request.scenario_id)
        return self.jobs.submit(operation, request, owner)
