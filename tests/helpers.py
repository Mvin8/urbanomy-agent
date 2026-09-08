import json
from pathlib import Path
import time
import os

import numpy as np

from urbanomy_agent.jobs import write_json
from urbanomy_agent.schemas import OptimizationRequest

def slow_worker(operation, payload, manifest, directory):
    time.sleep(30)


def result_worker(operation, payload, manifest, directory):
    directory = Path(directory)
    write_json(directory / "result.json", {"summary": "Measured result", "target_id": payload["target_id"]})
    write_json(directory / "scenarios.geojson", {"type": "FeatureCollection", "features": []})


def error_worker(operation, payload, manifest, directory):
    write_json(Path(directory) / "error.json", {"code": "CALCULATION_FAILED", "message": "Invalid test dataset"})


def crash_worker(operation, payload, manifest, directory):
    os._exit(2)


def wait_for_job(jobs, job_id, owner="mcp", timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = jobs.get(job_id, owner)
        if result["status"] != "working":
            return result
        time.sleep(.05)
    raise AssertionError(f"Job {job_id} did not finish in {timeout}s")


def request(**kwargs):
    return OptimizationRequest.model_validate(dict(scenario_id="test", target_id=86, constraints={"l": {"min": 1, "max": 8}},
                                                     strategy="Mixed use", **kwargs))


def rpc(client, method, params):
    response = client.post("/a2a", headers={"A2A-Version": "1.0"}, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    assert response.status_code == 200
    return response.json()


def send_params(immediate=False):
    return {"tenant": "test", "configuration": {"returnImmediately": immediate}, "message": {
        "messageId": "m-1", "contextId": "ctx-1", "role": "ROLE_USER", "parts": [
            {"data": {"operation": "estimate_land_value", "scenario_id": "test", "target_id": "86"}}]}}


def task_from(response):
    assert "error" not in response, response
    result = response["result"]
    return result.get("task", result)


class Model:
    feature_names_ = None

    def predict(self, frame):
        return np.log1p(frame.build_floor_area.to_numpy() * 1000)


def optimization(**kwargs):
    payload = dict(scenario_id="test", target_id=0, constraints={"l": {"min": 2, "max": 6}},
                   strategy="Prefer mixed uses", use_llm=False, pop_size=4, n_gen=2)
    payload.update(kwargs)
    return OptimizationRequest.model_validate(payload)

