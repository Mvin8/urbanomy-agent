import json
import pytest
from urbanomy_agent.data import DatasetRegistry, target_row

def test_registry_projects_geographic_crs_and_keeps_ids(blocks, tmp_path):
    blocks.to_crs(4326).to_file(tmp_path / "blocks.geojson", driver="GeoJSON")
    (tmp_path / "model.cbm").write_text("dummy")
    manifest = tmp_path / "datasets.json"
    manifest.write_text(json.dumps({"test": {"blocks_path": "blocks.geojson", "model_path": "model.cbm"}}))
    loaded = DatasetRegistry(manifest).blocks("test")
    assert loaded.crs.is_projected
    assert loaded.id.tolist() == [0, 1, 2]
    assert loaded.site_area.tolist() == blocks.site_area.tolist()


def register(blocks, tmp_path, **options):
    blocks.to_file(tmp_path / "blocks.geojson", driver="GeoJSON")
    (tmp_path / "model.cbm").write_text("dummy")
    manifest = tmp_path / "datasets.json"
    manifest.write_text(json.dumps({"test": {"blocks_path": "blocks.geojson", "model_path": "model.cbm", **options}}))
    return DatasetRegistry(manifest)


@pytest.mark.parametrize("dataset_id", ["../secret", "/private/data", "unknown"])
def test_invalid_dataset_never_reads_arbitrary_geometry(settings, monkeypatch, dataset_id):
    import geopandas as gpd
    monkeypatch.setattr(gpd, "read_file", lambda *_: pytest.fail("Invalid id must not open a geometry file"))
    with pytest.raises(ValueError):
        DatasetRegistry(settings.datasets_file).blocks(dataset_id)


def test_duplicate_block_ids_are_rejected(blocks, tmp_path):
    blocks.loc[1, "id"] = 0
    with pytest.raises(ValueError, match="unique"):
        register(blocks, tmp_path).blocks("test")


def test_target_selection_preserves_ids_and_rejects_missing_target(blocks):
    assert target_row(blocks, "1")["id"] == 1
    with pytest.raises(ValueError, match="found 0"):
        target_row(blocks, "999")


def test_geometry_repair_is_explicit_and_reported(blocks, tmp_path):
    from shapely.geometry import Polygon
    blocks.loc[0, "geometry"] = Polygon([(0, 0), (100, 100), (0, 100), (100, 0), (0, 0)])
    registry = register(blocks, tmp_path)
    with pytest.raises(ValueError, match="invalid geometries"):
        registry.blocks("test")
    spec = json.loads(registry.manifest.read_text())
    spec["test"]["geometry_policy"] = "repair_and_drop_non_polygon"
    registry.manifest.write_text(json.dumps(spec))
    repaired = registry.blocks("test")
    assert repaired.is_valid.all()
    assert repaired.attrs["preparation"]["repaired_ids"] == [0]
    assert repaired.id.tolist() == blocks.id.tolist()
