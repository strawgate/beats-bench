#!/usr/bin/env python3
"""summarize.py — Generate benchmark summary from all-results/ directory.

Reads runs.jsonl and results.txt from each scenario subdirectory,
produces summary.md and gh-bench.json for benchmark-action.

Usage:
    python3 scripts/summarize.py \
        --results-dir all-results \
        --base-ref main \
        --pr-ref feature-branch \
        --base-repo elastic/beats \
        --pr-repo elastic/beats \
        --runs-per-scenario 3 \
        --measure-seconds 20
"""

import argparse
import json
import os
import sys
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Summarize benchmark results")
    p.add_argument("--results-dir", required=True, help="Path to all-results directory")
    p.add_argument("--base-ref", required=True, help="Base git ref")
    p.add_argument("--pr-ref", required=True, help="PR git ref")
    p.add_argument("--base-repo", required=True, help="Base repo (owner/repo)")
    p.add_argument("--pr-repo", required=True, help="PR repo (owner/repo)")
    p.add_argument("--runs-per-scenario", type=int, required=True, help="Runs per scenario")
    p.add_argument("--measure-seconds", type=int, required=True, help="Measurement seconds")
    return p.parse_args()


def load_results(results_dir):
    """Load all scenario results from the results directory."""
    results = []
    results_path = Path(results_dir)

    if not results_path.exists():
        print(f"ERROR: results directory {results_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    for subdir in sorted(results_path.iterdir()):
        if not subdir.is_dir():
            continue

        results_txt = subdir / "results.txt"
        if not results_txt.exists():
            continue

        data = {"dir": subdir.name}

        # Parse results.txt (key=value)
        for line in results_txt.read_text().splitlines():
            if "=" in line:
                k, v = line.strip().split("=", 1)
                data[k] = v

        # Parse runs.jsonl for detailed per-run data
        runs_jsonl = subdir / "runs.jsonl"
        if runs_jsonl.exists():
            base_runs = []
            pr_runs = []
            for line in runs_jsonl.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    run = json.loads(line)
                    if run.get("label") == "base":
                        base_runs.append(run)
                    elif run.get("label") == "pr":
                        pr_runs.append(run)
                except json.JSONDecodeError:
                    continue
            data["base_runs"] = base_runs
            data["pr_runs"] = pr_runs

        if "scenario" in data and "base_eps" in data:
            results.append(data)

    return results


def generate_summary(results, args):
    """Generate the summary markdown and gh-bench.json data."""
    lines = []
    lines.append("## Filebeat Pipeline Benchmark Results\n")
    lines.append(f"**Base:** `{args.base_ref}` @ `{args.base_repo}`")
    lines.append(f"**PR:** `{args.pr_ref}` @ `{args.pr_repo}`")
    lines.append(
        f"**Runs per scenario:** {args.runs_per_scenario}, "
        f"**Measurement:** {args.measure_seconds}s per run\n"
    )

    # ---- Throughput table ----
    lines.append("### Throughput (events/sec)\n")
    lines.append("| Scenario | CPU | Base EPS | PR EPS | \u0394 |")
    lines.append("|---|---|---:|---:|---:|")

    gh_bench = []
    for r in results:
        base_vals = [int(x) for x in r["base_eps"].split(",") if x]
        pr_vals = [int(x) for x in r["pr_eps"].split(",") if x]
        if not base_vals or not pr_vals:
            continue

        base_avg = sum(base_vals) // len(base_vals)
        pr_avg = sum(pr_vals) // len(pr_vals)
        delta = (pr_avg - base_avg) * 100 // base_avg if base_avg > 0 else 0
        sign = "+" if delta >= 0 else ""
        scenario = r["scenario"]
        cpu = r["cpu"]
        base_str = f"{base_avg:,} ({'|'.join(str(v) for v in base_vals)})"
        pr_str = f"{pr_avg:,} ({'|'.join(str(v) for v in pr_vals)})"
        lines.append(f"| {scenario} | {cpu} | {base_str} | {pr_str} | **{sign}{delta}%** |")
        gh_bench.append({
            "name": f"{scenario} ({cpu} CPU)",
            "unit": "events/sec",
            "value": pr_avg,
            "extra": f"base={base_avg} delta={sign}{delta}%",
        })

    # ---- Resource usage table (from runs.jsonl) ----
    lines.append("\n### Resource usage (from final measurement run)\n")
    lines.append("| Scenario | CPU | Variant | Alloc (MB) | RSS (MB) | GC next (MB) | Goroutines |")
    lines.append("|---|---|---|---:|---:|---:|---:|")

    for r in results:
        scenario = r["scenario"]
        cpu = r["cpu"]
        for label, runs_key in [("base", "base_runs"), ("pr", "pr_runs")]:
            runs = r.get(runs_key, [])
            if not runs:
                continue
            # Use the last run's data
            last = runs[-1]
            alloc_mb = last.get("memory_alloc_mb", 0)
            rss_mb = last.get("memory_rss_mb", 0)
            gc_mb = last.get("gc_next_mb", 0)
            goroutines = last.get("goroutines", 0)
            lines.append(
                f"| {scenario} | {cpu} | {label} | "
                f"{alloc_mb:.1f} | {rss_mb:.1f} | {gc_mb:.1f} | {goroutines} |"
            )

    # ---- Mock-ES stats table (from runs.jsonl) ----
    lines.append("\n### Mock-ES sink stats (from final measurement run)\n")
    lines.append("| Scenario | CPU | Variant | Docs | Batches | Avg batch | Bytes (MB) | Docs/sec |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|")

    for r in results:
        scenario = r["scenario"]
        cpu = r["cpu"]
        for label, runs_key in [("base", "base_runs"), ("pr", "pr_runs")]:
            runs = r.get(runs_key, [])
            if not runs:
                continue
            last = runs[-1]
            docs = last.get("mock_docs", 0)
            batches = last.get("mock_batches", 0)
            avg_batch = last.get("mock_avg_batch", 0)
            bytes_mb = last.get("mock_bytes_mb", 0)
            dps = last.get("mock_docs_per_sec", 0)
            lines.append(
                f"| {scenario} | {cpu} | {label} | "
                f"{docs:,} | {batches:,} | {avg_batch:.0f} | {bytes_mb:.0f} | {dps:,.0f} |"
            )

    lines.append("\n\n*CPU/alloc/heap profiles available as workflow artifacts.*")

    return "\n".join(lines), gh_bench


def main():
    args = parse_args()
    results = load_results(args.results_dir)

    if not results:
        print("WARNING: no results found", file=sys.stderr)

    md, gh_bench = generate_summary(results, args)
    print(md)

    with open("summary.md", "w") as f:
        f.write(md)
    with open("gh-bench.json", "w") as f:
        json.dump(gh_bench, f, indent=2)

    print(f"\nWrote summary.md and gh-bench.json", file=sys.stderr)


if __name__ == "__main__":
    main()
