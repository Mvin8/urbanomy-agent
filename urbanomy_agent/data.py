"""Only administrator-registered datasets can be opened by remote callers."""
import hashlib
import json
from pathlib import Path

from pydantic import TypeAdapter

from .schemas import DatasetId


class DatasetRegistry:
    def __init__(self, manifest: Path):
        self.manifest = manifest

    def catalog(self):
        return json.loads(self.manifest.read_text())

    def list(self):
        return [{"dataset_id": key, "description": value.get("description", "")} for key, value in self.catalog().items()]

    def paths(self, dataset_id: str):
        TypeAdapter(DatasetId).validate_python(dataset_id)
        spec = self.catalog().get(dataset_id)
        if spec is None:
            raise ValueError(f"Unknown dataset_id: {dataset_id}. Use list_datasets.")
        paths = tuple((self.manifest.parent / spec[key]).resolve() for key in ("blocks_path", "model_path"))
        if not all(path.is_file() for path in paths):
            raise ValueError(f"Dataset {dataset_id} is not provisioned: blocks/model file is missing.")
        return paths

    def blocks(self, dataset_id: str):
        import geopandas as gpd
        import numpy as np
        import pandas as pd
        from urbanomy.land_value.constants import CATEGORICAL_FEATURES, ORIGINAL_FEATURES

        blocks_path, _ = self.paths(dataset_id)
        blocks = gpd.read_file(blocks_path)
        preparation = {"repaired_ids": [], "excluded_ids": []}
        missing = set((*ORIGINAL_FEATURES, "id")) - set(blocks.columns)
        if missing:
            raise ValueError(f"Missing dataset columns: {sorted(missing)}")
        if blocks.empty or blocks.id.isna().any() or not blocks.id.astype(str).is_unique:
            raise ValueError("Dataset requires non-empty, unique block ids.")
        if blocks.crs is None:
            raise ValueError("Dataset CRS is required.")
        if self.catalog()[dataset_id].get("geometry_policy") == "repair_and_drop_non_polygon":
            from shapely import union_all

            invalid = ~blocks.geometry.is_valid
            preparation["repaired_ids"] = blocks.loc[invalid, "id"].tolist()
            blocks.loc[invalid, "geometry"] = blocks.loc[invalid].geometry.make_valid()
            def polygonal(geometry):
                if geometry is not None and geometry.geom_type == "GeometryCollection":
                    return union_all([part for part in geometry.geoms if part.geom_type in ("Polygon", "MultiPolygon")])
                return geometry
            blocks.geometry = blocks.geometry.map(polygonal)
            keep = blocks.geom_type.isin(["Polygon", "MultiPolygon"]) & ~blocks.geometry.is_empty & blocks.geometry.is_valid
            preparation["excluded_ids"] = blocks.loc[~keep, "id"].tolist()
            blocks = blocks.loc[keep].copy()
        if blocks.empty or blocks.geometry.isna().any() or blocks.geometry.is_empty.any() or not blocks.geometry.is_valid.all():
            raise ValueError("Dataset contains missing, empty or invalid geometries.")
        if blocks.crs.is_geographic:
            metric_crs = blocks.estimate_utm_crs()
            if metric_crs is None:
                raise ValueError("Cannot determine a metric CRS; register projected data.")
            blocks = blocks.to_crs(metric_crs)
        if not blocks.crs.is_projected or any(abs(axis.unit_conversion_factor - 1) > 1e-9 for axis in blocks.crs.axis_info):
            raise ValueError("Spatial calculations require a projected CRS in metres.")
        numeric = [key for key in ORIGINAL_FEATURES if key not in CATEGORICAL_FEATURES]
        blocks[numeric] = blocks[numeric].apply(pd.to_numeric, errors="raise")
        if np.isinf(blocks[numeric].to_numpy(dtype=float)).any() or not np.isfinite(blocks.site_area).all() or (blocks.site_area <= 0).any():
            raise ValueError("Numeric features cannot contain infinity; site_area must be finite and positive.")
        # Preserve the estimator's existing missing-value semantics: CatBoost handles
        # numeric NaNs, spatial lags use column means, categories use 'missing'.
        preparation["missing_values"] = {key: int(value) for key, value in blocks[list(ORIGINAL_FEATURES)].isna().sum().items() if value}
        blocks.attrs["preparation"] = preparation
        return blocks

    def load(self, dataset_id: str):
        from catboost import CatBoostRegressor

        paths = self.paths(dataset_id)
        model = CatBoostRegressor(thread_count=1)
        model.load_model(str(paths[1]))
        provenance = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in zip(("blocks_sha256", "model_sha256"), paths)}
        blocks = self.blocks(dataset_id)
        provenance.update(blocks.attrs["preparation"])
        return blocks, model, provenance


def target_row(blocks, target_id):
    matches = blocks[blocks["id"].astype(str) == str(target_id)]
    if len(matches) != 1:
        raise ValueError(f"Expected one block with id={target_id!r}, found {len(matches)}. Use list_blocks.")
    return matches.iloc[0]
