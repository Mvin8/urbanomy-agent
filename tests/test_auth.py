from fastapi.testclient import TestClient
from urbanomy_agent.server import build_app
from tests.helpers import rpc, send_params, task_from


def test_a2a_invalid_request_and_auth(settings):
    from dataclasses import replace
    settings = replace(settings, token="test-secret")
    with TestClient(build_app(settings)) as client:
        assert client.post("/a2a", json={}).status_code == 401
        assert client.post("/mcp", json={}).status_code == 401
        assert client.get("/.well-known/agent-card.json").status_code == 200
        client.headers["authorization"] = "Bearer test-secret"
        params = send_params()
        params["message"]["parts"][0]["data"]["target_id"] = True
        task = task_from(rpc(client, "SendMessage", params))
        assert task["status"]["state"] == "TASK_STATE_FAILED"
        assert "INVALID_REQUEST" in task["status"]["message"]["parts"][0]["text"]

