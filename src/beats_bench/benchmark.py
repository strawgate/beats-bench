"""Run a benchmark: warmup + N measurement runs + optional profiles.

Replaces the old alternating base/PR scenario runner.  This module runs
a *single* binary repeatedly and emits results in benchmark-action JSON
format so benchkit actions (stash / aggregate / compare) can consume them.
"""

from __future__ import annotations

import json
import os
import sys
import time

from beats_bench.docker import (
    ensure_network,
    start_filebeat,
    start_mock_es,
    stop_all,
    wait_for_endpoint,
)
from beats_bench.profiler import collect_profiles
from beats_bench.runner import RunResult, run_one


def _to_benchmark_entries(
    results: list[RunResult],
    scenario: str,
    cpu: str,
) -> list[dict]:
    """Convert a list of RunResult into benchmark-action JSON entries.

    Emits one entry per metric using the *median* across runs (more robust
    against outliers than mean for small sample sizes).
    """
    if not results:
        return []

    def _median(values: list[float]) -> float:
        s = sorted(values)
        n = len(s)
        if n % 2 == 1:
            return s[n // 2]
        return (s[n // 2 - 1] + s[n // 2]) / 2

    name_prefix = f"{scenario} ({cpu} CPU)"

    eps_vals = [float(r.eps) for r in results]
    entries: list[dict] = [
        {
            "name": name_prefix,
            "unit": "events/s",
            "value": _median(eps_vals),
        },
    ]

    alloc_vals = [r.alloc_per_event for r in results]
    if any(v > 0 for v in alloc_vals):
        entries.append(
            {
                "name": f"{name_prefix} alloc_per_event",
                "unit": "bytes/event",
                "value": _median(alloc_vals),
            }
        )

    rss_vals = [r.memory_rss_mb for r in results]
    if any(v > 0 for v in rss_vals):
        entries.append(
            {
                "name": f"{name_prefix} memory_rss",
                "unit": "MB",
                "value": round(_median(rss_vals), 2),
            }
        )

    alloc_mb_vals = [r.memory_alloc_mb for r in results]
    if any(v > 0 for v in alloc_mb_vals):
        entries.append(
            {
                "name": f"{name_prefix} memory_alloc",
                "unit": "MB",
                "value": round(_median(alloc_mb_vals), 2),
            }
        )

    return entries


def run_benchmark(
    binary: str,
    config: str,
    mock_es: str,
    cpus: str,
    measure: int,
    runs: int,
    output_dir: str,
    scenario_name: str | None = None,
    *,
    collect_pprof: bool = True,
) -> list[RunResult]:
    """Run a full benchmark: warmup + N measurement runs + optional profiles.

    Writes ``results.json`` (benchmark-action format) and ``runs.jsonl``
    (detailed per-run data) to *output_dir*.
    """
    os.makedirs(output_dir, exist_ok=True)
    ensure_network()

    name = scenario_name or os.path.splitext(os.path.basename(config))[0]

    # Warmup (discarded)
    print("=== Warmup run (discarded) ===")
    run_one(binary, config, mock_es, cpus, measure, "warmup")

    # Measurement runs
    all_results: list[RunResult] = []
    jsonl_path = os.path.join(output_dir, "runs.jsonl")

    with open(jsonl_path, "w") as jsonl_file:
        for i in range(1, runs + 1):
            print(f"=== Measurement run {i}/{runs} ===")
            result = run_one(binary, config, mock_es, cpus, measure, "measurement")
            jsonl_file.write(json.dumps(result.to_dict()) + "\n")
            jsonl_file.flush()
            all_results.append(result)
            print(f"  Run {i}: {result.eps} events/s")

    # Profile collection
    if collect_pprof:
        print("=== Collecting profiles ===")
        stop_all()

        start_mock_es(os.path.abspath(mock_es))
        if not wait_for_endpoint("http://localhost:9200/"):
            print("ERROR: mock-es did not start for profiling", file=sys.stderr)
        else:
            start_filebeat(os.path.abspath(binary), os.path.abspath(config), cpus)
            if not wait_for_endpoint("http://localhost:5066/stats"):
                print("ERROR: filebeat did not start for profiling", file=sys.stderr)
            else:
                time.sleep(5)
                collect_profiles(output_dir, "profile", measure)

        stop_all()

    # Write benchmark-action format results
    entries = _to_benchmark_entries(all_results, name, cpus)
    results_path = os.path.join(output_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(entries, f, indent=2)

    print("=== Results ===")
    for entry in entries:
        print(f"  {entry['name']}: {entry['value']} {entry['unit']}")
    print(f"=== Benchmark complete. Output in {output_dir}/ ===")

    return all_results
