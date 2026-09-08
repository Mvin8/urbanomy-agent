import json
import pytest
from urbanomy_agent.data import ScenarioRegistry, target_row

def test_registry_projects_geographic_crs_and_keeps_ids(blocks, tmp_path):
    loaded = register(blocks.to_crs(4326), tmp_path).blocks("test")
    assert loaded.crs.is_projected
    assert loaded.id.tolist() == [0, 1, 2]
    assert loaded.site_area.tolist() == blocks.site_area.tolist()


def register(blocks, tmp_path, **options):
    scenario = tmp_path / "test"
    scenario.mkdir(exist_ok=True)
    blocks.to_file(scenario / ScenarioRegistry.BLOCKS_FILE, driver="GeoJSON")
    (scenario / ScenarioRegistry.MODEL_FILE).write_text("dummy")
    (scenario / "scenario.json").write_text(json.dumps(options))
    return ScenarioRegistry(tmp_path)


@pytest.mark.parametrize("scenario_id", ["../secret", "/private/data", "unknown"])
def test_invalid_dataset_never_reads_arbitrary_geometry(settings, monkeypatch, scenario_id):
    import geopandas as gpd
    monkeypatch.setattr(gpd, "read_file", lambda *_: pytest.fail("Invalid id must not open a geometry file"))
    with pytest.raises(ValueError):
        ScenarioRegistry(settings.data_dir).blocks(scenario_id)


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
    (tmp_path / "test/scenario.json").write_text(json.dumps({"geometry_policy": "repair_and_drop_non_polygon"}))
    repaired = registry.blocks("test")
    assert repaired.is_valid.all()
    assert repaired.attrs["preparation"]["repaired_ids"] == [0]
    assert repaired.id.tolist() == blocks.id.tolist()


def test_directory_catalog_and_missing_scenario_hint(blocks, tmp_path):
    from urbanomy_agent.data import ContextError
    registry = register(blocks, tmp_path)
    (tmp_path / "incomplete").mkdir()
    assert registry.list() == [{"scenario_id": "test"}]
    with pytest.raises(ContextError) as error:
        registry.paths("incomplete")
    assert error.value.code == "SCENARIO_NOT_MATERIALIZED"
    assert "available scenarios: test" in str(error.value)
    assert str(tmp_path) not in str(error.value)


@pytest.mark.parametrize("link_kind", ["directory", "blocks", "model", "metadata"])
def test_symlinks_outside_data_dir_are_rejected(blocks, tmp_path, link_kind):
    from urbanomy_agent.data import ContextError
    root = tmp_path / "data"
    root.mkdir()
    registry = register(blocks, root)
    outside = tmp_path / "outside"
    outside.mkdir()
    if link_kind == "directory":
        (root / "escape").symlink_to(outside, target_is_directory=True)
        check = lambda: registry.paths("escape")
    else:
        name = {"blocks": registry.BLOCKS_FILE, "model": registry.MODEL_FILE,
                "metadata": "scenario.json"}[link_kind]
        (outside / name).write_text("{}")
        (root / "test" / name).unlink()
        (root / "test" / name).symlink_to(outside / name)
        check = lambda: registry.blocks("test")
    with pytest.raises(ContextError, match="VALIDATION_ERROR"):
        check()


def test_missing_root_has_empty_catalog(tmp_path):
    registry = ScenarioRegistry(tmp_path / "missing")
    assert registry.list() == []
    with pytest.raises(ValueError, match="SCENARIO_NOT_MATERIALIZED"):
        registry.paths("test")
