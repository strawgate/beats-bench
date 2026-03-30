"""Orchestrate warmup + alternating runs + profile collection (replaces run-scenario.sh)."""

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


def run_scenario(
    base_bin: str,
    pr_bin: str,
    config: str,
    mock_es: str,
    cpus: str,
    measure: int,
    runs: int,
    output_dir: str,
    scenario_name: str | None = None,
) -> list[RunResult]:
    """Run a full benchmark scenario: warmup + N alternating runs + profiles."""
    os.makedirs(output_dir, exist_ok=True)
    ensure_network()

    # Warmup (discarded)
    print("=== Warmup run (discarded) ===")
    run_one(base_bin, config, mock_es, cpus, measure, "warmup")

    # Alternating measurement runs
    base_eps_list: list[int] = []
    pr_eps_list: list[int] = []
    all_results: list[RunResult] = []
    jsonl_path = os.path.join(output_dir, "runs.jsonl")

    with open(jsonl_path, "w") as jsonl_file:
        for i in range(1, runs + 1):
            if i % 2 == 1:
                first_label, first_bin = "base", base_bin
                second_label, second_bin = "pr", pr_bin
            else:
                first_label, first_bin = "pr", pr_bin
                second_label, second_bin = "base", base_bin

            print(f"=== Run {i}/{runs}: {first_label} first ===")

            first_result = run_one(first_bin, config, mock_es, cpus, measure, first_label)
            jsonl_file.write(json.dumps(first_result.to_dict()) + "\n")
            jsonl_file.flush()
            all_results.append(first_result)

            second_result = run_one(second_bin, config, mock_es, cpus, measure, second_label)
            jsonl_file.write(json.dumps(second_result.to_dict()) + "\n")
            jsonl_file.flush()
            all_results.append(second_result)

            if first_label == "base":
                base_eps_list.append(first_result.eps)
                pr_eps_list.append(second_result.eps)
            else:
                base_eps_list.append(second_result.eps)
                pr_eps_list.append(first_result.eps)

            print(f"  Run {i}: base={base_eps_list[-1]} pr={pr_eps_list[-1]}")

    # Profile collection
    for label, binary in [("base", base_bin), ("pr", pr_bin)]:
        print(f"=== Collecting profiles for {label} ===")
        stop_all()

        start_mock_es(os.path.abspath(mock_es))
        if not wait_for_endpoint("http://localhost:9200/"):
            print("ERROR: mock-es did not start for profiling", file=sys.stderr)
            continue

        start_filebeat(os.path.abspath(binary), os.path.abspath(config), cpus)
        if not wait_for_endpoint("http://localhost:5066/stats"):
            print("ERROR: filebeat did not start for profiling", file=sys.stderr)
            stop_all()
            continue

        time.sleep(5)
        collect_profiles(output_dir, label, measure)
        stop_all()

    # Write results.txt
    name = scenario_name or os.path.splitext(os.path.basename(config))[0]
    results_path = os.path.join(output_dir, "results.txt")
    with open(results_path, "w") as f:
        f.write(f"scenario={name}\n")
        f.write(f"cpu={cpus}\n")
        f.write(f"base_eps={','.join(str(e) for e in base_eps_list)}\n")
        f.write(f"pr_eps={','.join(str(e) for e in pr_eps_list)}\n")

    print("=== Results ===")
    with open(results_path) as f:
        print(f.read(), end="")
    print(f"=== Benchmark complete. Output in {output_dir}/ ===")

    return all_results
