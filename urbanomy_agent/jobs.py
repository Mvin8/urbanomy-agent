"""Bounded, cancellable worker processes with local result artifacts."""
from contextlib import redirect_stderr, redirect_stdout
import json
import multiprocessing
import os
from pathlib import Path
import threading
import time
import traceback
import uuid

from .schemas import EstimateRequest, OptimizationRequest

TERMINAL = {"completed", "failed", "canceled"}


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def worker(operation, payload, manifest, directory):
    directory = Path(directory)
    with (directory / "worker.log").open("w") as log, redirect_stdout(log), redirect_stderr(log):
        # Native scientific libraries may write directly to file descriptors.
        # Never let a worker emit bytes into its parent's MCP stdio channel.
        os.dup2(log.fileno(), 1)
        os.dup2(log.fileno(), 2)
        try:
            from .engine import execute

            schema = OptimizationRequest if operation == "optimize_district" else EstimateRequest
            result, spatial = execute(operation, schema.model_validate(payload), Path(manifest),
                                      lambda progress: write_json(directory / "progress.json", progress))
            if hasattr(spatial, "to_crs"):
                spatial = json.loads(spatial.to_crs(4326).to_json())
            write_json(directory / "scenarios.geojson", spatial)
            write_json(directory / "result.json", result)
        except Exception as exc:
            traceback.print_exc()
            message = str(exc) if isinstance(exc, ValueError) else "Calculation failed. See the server worker log."
            write_json(directory / "error.json", {"code": "CALCULATION_FAILED", "message": message})


class JobManager:
    def __init__(self, settings, runner=worker):
        self.settings = settings
        self.runner = runner
        self.records = {}
        self.lock = threading.RLock()
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()

    def submit(self, operation, request, owner="mcp"):
        with self.lock:
            if self.stopped.is_set():
                raise ValueError("Server is shutting down.")
            if sum(r["status"] not in TERMINAL for r in self.records.values()) >= self.settings.max_jobs:
                raise ValueError("SERVER_BUSY: concurrent job limit reached. Retry after an active job completes.")
            job_id = uuid.uuid4().hex
            directory = self.settings.output_dir / job_id
            directory.mkdir(parents=True)
            payload = request.model_dump(mode="json")
            write_json(directory / "request.json", {"operation": operation, **payload})
            process = multiprocessing.get_context("spawn").Process(
                target=self.runner, args=(operation, payload, str(self.settings.datasets_file), str(directory)), daemon=True,
            )
            record = {"job_id": job_id, "operation": operation, "status": "working", "owner": owner,
                      "directory": directory, "process": process, "started": time.monotonic()}
            process.start()
            self.records[job_id] = record
            return self.get(job_id, owner)

    def _refresh(self, record):
        if record["status"] in TERMINAL:
            return
        directory, process = record["directory"], record["process"]
        if process.is_alive():
            if time.monotonic() - record["started"] > self.settings.timeout_seconds:
                self._stop(process)
                record.update(status="failed", error={"code": "TIMEOUT", "message": "Job exceeded the server time limit."})
            return
        process.join()
        if (directory / "error.json").exists():
            record.update(status="failed", error=json.loads((directory / "error.json").read_text()))
        elif process.exitcode == 0 and (directory / "result.json").exists():
            record["status"] = "completed"
        else:
            record.update(status="failed", error={"code": "WORKER_EXITED", "message": "Worker exited without a result."})

    def _record(self, job_id, owner):
        record = self.records.get(job_id)
        if record is None or record["owner"] != owner:
            raise ValueError("JOB_NOT_FOUND")
        self._refresh(record)
        return record

    def get(self, job_id, owner="mcp"):
        with self.lock:
            record = self._record(job_id, owner)
            result = {key: record[key] for key in ("job_id", "operation", "status")}
            result["elapsed_seconds"] = round(time.monotonic() - record["started"], 1)
            if "error" in record:
                result["error"] = record["error"]
            progress = record["directory"] / "progress.json"
            if progress.exists():
                result["progress"] = json.loads(progress.read_text())
            return result

    def result(self, job_id, owner="mcp"):
        with self.lock:
            status = self.get(job_id, owner)
            if status["status"] == "completed":
                directory = self.records[job_id]["directory"]
                status["result"] = json.loads((directory / "result.json").read_text())
            return status

    def geojson(self, job_id, owner="mcp"):
        with self.lock:
            record = self._record(job_id, owner)
            if record["status"] != "completed":
                raise ValueError("Job is not completed.")
            return json.loads((record["directory"] / "scenarios.geojson").read_text())

    @staticmethod
    def _stop(process):
        if process.is_alive():
            process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)

    def cancel(self, job_id, owner="mcp"):
        with self.lock:
            record = self._record(job_id, owner)
            if record["status"] not in TERMINAL:
                self._stop(record["process"])
                record["status"] = "canceled"
            return self.get(job_id, owner)

    def _monitor(self):
        while not self.stopped.wait(0.5):
            with self.lock:
                for record in list(self.records.values()):
                    self._refresh(record)
                    if record["status"] in TERMINAL and time.monotonic() - record["started"] > 86400:
                        del self.records[record["job_id"]]

    def close(self):
        self.stopped.set()
        self.thread.join(timeout=5)
        with self.lock:
            for record in self.records.values():
                self._stop(record["process"])
                if record["status"] not in TERMINAL:
                    record["status"] = "canceled"
