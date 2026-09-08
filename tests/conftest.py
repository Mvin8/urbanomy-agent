"""Synthetic data and isolated settings; no local dataset or LLM account required."""
import json
import os
from pathlib import Path
import tempfile

import pytest

from urbanomy_agent.settings import Settings

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "urbanomy-test-matplotlib"))


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """Never inherit a developer's provider credentials, URLs or job settings."""
    for key in list(os.environ):
        if key.startswith(("URBANOMY_", "OPENAI_", "FP2MP_", "CHAT_")) or key in {"API_KEY", "MODEL_NAME", "DATA_DIR"}:
            monkeypatch.delenv(key)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")

@pytest.fixture
def settings(tmp_path):
    scenario = tmp_path / "test"
    scenario.mkdir()
    (scenario / "blocks_agg_with_indicators.geojson").write_text("{}")
    (scenario / "catboost_land_value_no_services.cbm").write_text("test")
    return Settings(data_dir=tmp_path, output_dir=tmp_path / "jobs", max_jobs=2, timeout_seconds=10)



@pytest.fixture
def blocks():
    import geopandas as gpd
    from shapely.geometry import box

    row = {"residential": .6, "business": .2, "recreation": .2, "industrial": 0., "transport": 0.,
           "special": 0., "agriculture": 0., "land_use": "LandUse.RESIDENTIAL", "share": .6,
           "footprint_area": 2000., "build_floor_area": 8000., "living_area": 3840., "non_living_area": 4160.,
           "population": 192., "site_area": 10000., "fsi": .8, "gsi": .2, "mxi": .48, "l": 4.,
           "morphotype": "individual residential", "area_accessibility": 10.}
    return gpd.GeoDataFrame([{**row, "id": i, "geometry": box(i * 150, 0, i * 150 + 100, 100)}
                            for i in range(3)], crs=32636)
