from pathlib import Path

import pytest

from urbanomy_agent.settings import Settings


def test_environment_overrides_paths_and_runtime_limits(monkeypatch, tmp_path):
    values = {"URBANOMY_DATASETS": str(tmp_path / "datasets.json"), "URBANOMY_OUTPUT_DIR": str(tmp_path / "results"),
              "URBANOMY_PORT": "9000", "URBANOMY_MAX_JOBS": "3", "URBANOMY_JOB_TIMEOUT": "12",
              "URBANOMY_PUBLIC_URL": "https://example.invalid", "URBANOMY_API_TOKEN": "hidden-value"}
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    settings = Settings()
    assert settings.datasets_file == tmp_path / "datasets.json"
    assert settings.output_dir == tmp_path / "results"
    assert (settings.port, settings.max_jobs, settings.timeout_seconds) == (9000, 3, 12)
    assert settings.public_url == "https://example.invalid"
    assert "hidden-value" not in repr(settings)


@pytest.mark.parametrize("overrides", [{"max_jobs": 0}, {"timeout_seconds": 0}])
def test_nonpositive_runtime_limits_are_rejected(overrides):
    with pytest.raises(ValueError, match="positive"):
        Settings(**overrides)
