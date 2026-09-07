"""Validate against the receiving system's schema, supplied explicitly by the developer."""
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from urbanomy_agent.jobs import JobManager
from urbanomy_agent.server import build_app
from urbanomy_agent.service import UrbanomyService
from tests.helpers import result_worker, rpc, send_params, task_from


@pytest.fixture
def contract_validator():
    directory = os.getenv("A2A_CONTRACTS_DIR")
    if not directory:
        pytest.skip("Set A2A_CONTRACTS_DIR to Codesynapse docs/contracts/a2a to run external contract checks.")
    path = Path(directory) / "synapse-a2a-1.0.schema.json"
    assert path.is_file(), f"Explicit A2A_CONTRACTS_DIR does not contain {path.name}: {path}"
    schema = json.loads(path.read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_card_completed_task_and_artifacts_match_codesynapse(settings, contract_validator):
    service = UrbanomyService(settings, JobManager(settings, runner=result_worker))
    with TestClient(build_app(settings, service)) as client:
        contract_validator.validate(client.get("/.well-known/agent-card.json").json())
        task = task_from(rpc(client, "SendMessage", send_params()))
        contract_validator.validate(task)
        for artifact in task["artifacts"]:
            contract_validator.validate(artifact)


def test_stream_updates_match_codesynapse(settings, contract_validator):
    service = UrbanomyService(settings, JobManager(settings, runner=result_worker))
    with TestClient(build_app(settings, service)) as client:
        response = client.post("/a2a", headers={"A2A-Version": "1.0"}, json={
            "jsonrpc": "2.0", "id": 1, "method": "SendStreamingMessage", "params": send_params()})
        updates = []
        for line in response.text.splitlines():
            if line.startswith("data:"):
                payload = json.loads(line[5:].strip())["result"]
                for value in payload.values():
                    contract_validator.validate(value)
                    updates.append(value)
        assert updates, response.text
        assert any(u.get("status", {}).get("state") == "TASK_STATE_COMPLETED" for u in updates)
