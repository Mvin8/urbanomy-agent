"""Run local baseline examples and sample service/worker resources; no LLM calls.

Requires the optional measurement dependency psutil. Writes to --output only.
"""
import argparse
import importlib.metadata
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

from urbanomy_agent.service import UrbanomyService
from urbanomy_agent.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/integration")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    requests = {name: json.loads((ROOT / f"examples/integration/{name}.request.json").read_text())
                for name in ("estimate", "optimize")}
    settings = Settings(data_dir=ROOT / "data", output_dir=output / "jobs", token="", max_jobs=2,
                        timeout_seconds=600)
    started = time.monotonic()
    service = UrbanomyService(settings)
    init_seconds = time.monotonic() - started
    parent = psutil.Process()
    samples = []
    try:
        for name, concurrency in (("estimate", 1), ("optimize", 1), ("optimize", 2)):
            for repeat in range(1, 4):
                operation = "estimate_land_value" if name == "estimate" else "optimize_district"
                started = time.monotonic()
                jobs = [service.submit(operation, requests[name]) for _ in range(concurrency)]
                peak_rss = 0
                cpu_start, cpu_last = {}, {}
                while True:
                    rss = 0
                    for proc in [parent, *parent.children(recursive=True)]:
                        try:
                            key = (proc.pid, proc.create_time())
                            rss += proc.memory_info().rss
                            usage = proc.cpu_times()
                            total = usage.user + usage.system
                            # Children are created after measurement starts.
                            cpu_start.setdefault(key, total if proc.pid == parent.pid else 0)
                            cpu_last[key] = total
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    peak_rss = max(peak_rss, rss)
                    states = [service.jobs.get(job["job_id"]) for job in jobs]
                    if all(state["status"] != "working" for state in states):
                        break
                    time.sleep(0.1)
                seconds = time.monotonic() - started
                for job, state in zip(jobs, states):
                    if state["status"] != "completed":
                        raise RuntimeError(state)
                    response = service.jobs.result(job["job_id"])
                    result = response["result"]
                    if name == "estimate":
                        assert result["land_value"] > 0 and result["currency"] == "RUB"
                    else:
                        assert result["scenarios"] and result["use_llm"] is False
                        assert result["strategy"] == requests[name]["strategy"]
                        for scenario in result["scenarios"]:
                            params = scenario["params_repaired"]
                            for key, bounds in result["effective_constraints"].items():
                                value = params[key]
                                tolerance = 1e-7 * max(1, abs(bounds["min"]), abs(bounds["max"]))
                                assert bounds["min"] - tolerance <= value <= bounds["max"] + tolerance, key
                    if concurrency == 1 and repeat == 1:
                        save(output / f"{name}.response.json", response)
                        save(output / f"{name}.geojson", service.jobs.geojson(job["job_id"]))
                cpu = sum(cpu_last[key] - cpu_start[key] for key in cpu_last)
                sample = dict(operation=name, concurrency=concurrency, repeat=repeat,
                              wall_seconds=round(seconds, 3), peak_tree_rss_mib=round(peak_rss / 2**20, 1),
                              sampled_cpu_seconds=round(cpu, 3), average_cpu_percent=round(cpu / seconds * 100, 1))
                samples.append(sample)
                print(json.dumps(sample), flush=True)
    finally:
        service.jobs.close()
    report = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "environment": {"os": platform.platform(), "architecture": platform.machine(),
                        "python": platform.python_version(), "logical_cpus": psutil.cpu_count(),
                        "physical_cpus": psutil.cpu_count(logical=False),
                        "system_ram_gib": round(psutil.virtual_memory().total / 2**30, 1),
                        "packages": {name: importlib.metadata.version(name) for name in
                                     ("catboost", "numpy", "pandas", "geopandas", "shapely", "pymoo", "psutil")}},
        "method": "UrbanomyService + spawned workers, no HTTP transport or LLM; process-tree RSS and CPU sampled every 0.1s. RSS includes shared pages per process; CPU is a sampled lower estimate. 100% CPU means one logical core. Wall time includes worker startup, calculation, artifact writes and polling.",
        "service_init_seconds": round(init_seconds, 6),
        "service_init_scope": "Constructor only; excludes Python/import startup and loading data/model.",
        "samples": samples,
        "summary": [dict(operation=name, concurrency=n,
                         median_wall_seconds=round(statistics.median(s["wall_seconds"] for s in samples if s["operation"] == name and s["concurrency"] == n), 3),
                         max_tree_rss_mib=max(s["peak_tree_rss_mib"] for s in samples if s["operation"] == name and s["concurrency"] == n))
                    for name, n in (("estimate", 1), ("optimize", 1), ("optimize", 2))],
    }
    save(output / "benchmark.json", report)


if __name__ == "__main__":
    main()
