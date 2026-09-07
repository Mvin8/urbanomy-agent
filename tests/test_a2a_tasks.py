from fastapi.testclient import TestClient
from urbanomy_agent.server import build_app
from urbanomy_agent.jobs import JobManager
from urbanomy_agent.service import UrbanomyService
from tests.helpers import result_worker, slow_worker, rpc, send_params, task_from


def test_a2a_card_and_complete_task(settings):
    service = UrbanomyService(settings, JobManager(settings, runner=result_worker))
    with TestClient(build_app(settings, service)) as client:
        card = client.get("/.well-known/agent-card.json").json()
        assert card["supportedInterfaces"][0]["protocolVersion"] == "1.0"
        assert card["capabilities"]["streaming"]
        task = task_from(rpc(client, "message/send", send_params()))
        assert task["status"]["state"] == "TASK_STATE_COMPLETED", task
        assert task["contextId"] == "ctx-1"
        assert len(task["artifacts"]) == 2
        assert task["artifacts"][0]["parts"][1]["data"]["target_id"] == "86"
        polled = task_from(rpc(client, "GetTask", {"id": task["id"], "tenant": "test"}))
        assert polled["status"]["state"] == "TASK_STATE_COMPLETED"
        assert "error" in rpc(client, "GetTask", {"id": task["id"], "tenant": "other"})



def test_a2a_async_cancel(settings):
    service = UrbanomyService(settings, JobManager(settings, runner=slow_worker))
    with TestClient(build_app(settings, service)) as client:
        task = task_from(rpc(client, "SendMessage", send_params(True)))
        assert task["status"]["state"] in ("TASK_STATE_SUBMITTED", "TASK_STATE_WORKING")
        canceled = task_from(rpc(client, "tasks/cancel", {"id": task["id"], "tenant": "test"}))
        assert canceled["status"]["state"] == "TASK_STATE_CANCELED"
        assert all(not r["process"].is_alive() for r in service.jobs.records.values())



def test_a2a_stream_has_terminal_event_and_artifacts(settings):
    service = UrbanomyService(settings, JobManager(settings, runner=result_worker))
    with TestClient(build_app(settings, service)) as client:
        response = client.post("/a2a", headers={"A2A-Version": "1.0"}, json={
            "jsonrpc": "2.0", "id": 1, "method": "SendStreamingMessage", "params": send_params()})
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "TASK_STATE_COMPLETED" in response.text
        assert "Measured result" in response.text
        assert "scenarios.geojson" in response.text

