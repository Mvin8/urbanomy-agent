import time
import pytest
from urbanomy_agent.jobs import JobManager
from tests.helpers import request, slow_worker
from tests.helpers import result_worker, error_worker, crash_worker, wait_for_job


def test_cancel_isolated_and_owner_enforced(settings):
    jobs = JobManager(settings, runner=slow_worker)
    try:
        a = jobs.submit("optimize_district", request(), "a")
        b = jobs.submit("optimize_district", request(), "b")
        with pytest.raises(ValueError, match="JOB_NOT_FOUND"):
            jobs.cancel(a["job_id"], "b")
        with pytest.raises(ValueError, match="SERVER_BUSY"):
            jobs.submit("optimize_district", request())
        assert jobs.cancel(a["job_id"], "a")["status"] == "canceled"
        assert not jobs.records[a["job_id"]]["process"].is_alive()
        assert jobs.get(b["job_id"], "b")["status"] == "working"
    finally:
        jobs.close()



def test_timeout_stops_worker(settings):
    from dataclasses import replace
    jobs = JobManager(replace(settings, timeout_seconds=1), runner=slow_worker)
    try:
        job = jobs.submit("optimize_district", request())
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline and jobs.get(job["job_id"])["status"] == "working":
            time.sleep(.1)
        assert jobs.get(job["job_id"])["error"]["code"] == "TIMEOUT"
        assert not jobs.records[job["job_id"]]["process"].is_alive()
    finally:
        jobs.close()


def test_completed_result_survives_cancel_and_releases_slot(settings):
    from dataclasses import replace
    jobs = JobManager(replace(settings, max_jobs=1), runner=result_worker)
    try:
        first = jobs.submit("optimize_district", request())
        assert wait_for_job(jobs, first["job_id"])["status"] == "completed"
        assert jobs.cancel(first["job_id"])["status"] == "completed"
        assert jobs.result(first["job_id"])["result"]["target_id"] == 86
        second = jobs.submit("optimize_district", request())
        assert second["job_id"] != first["job_id"]
    finally:
        jobs.close()


@pytest.mark.parametrize("runner,code", [(error_worker, "CALCULATION_FAILED"), (crash_worker, "WORKER_EXITED")])
def test_worker_failure_does_not_become_success(settings, runner, code):
    jobs = JobManager(settings, runner=runner)
    try:
        job = jobs.submit("optimize_district", request())
        status = wait_for_job(jobs, job["job_id"])
        assert status["status"] == "failed"
        assert status["error"]["code"] == code
        assert "result" not in jobs.result(job["job_id"])
        with pytest.raises(ValueError, match="not completed"):
            jobs.geojson(job["job_id"])
    finally:
        jobs.close()


def test_shutdown_stops_active_workers_and_rejects_new_jobs(settings):
    jobs = JobManager(settings, runner=slow_worker)
    job = jobs.submit("optimize_district", request())
    process = jobs.records[job["job_id"]]["process"]
    jobs.close()
    assert not process.is_alive()
    with pytest.raises(ValueError, match="shutting down"):
        jobs.submit("optimize_district", request())
