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

    # ---- Per-event efficiency table ----
    lines.append("\n### Per-event efficiency (from final measurement run)\n")
    lines.append("| Scenario | CPU | Variant | Bytes/event | Alloc/event | CPU ticks |")
    lines.append("|---|---|---|---:|---:|---:|")

    for r in results:
        scenario = r["scenario"]
        cpu = r["cpu"]
        for label, runs_key in [("base", "base_runs"), ("pr", "pr_runs")]:
            runs = r.get(runs_key, [])
            if not runs:
                continue
            last = runs[-1]
            bpe = last.get("bytes_per_event", 0)
            ape = last.get("alloc_per_event", 0)
            cpu_ticks = last.get("cpu_ticks", 0)
            lines.append(
                f"| {scenario} | {cpu} | {label} | "
                f"{bpe:,.0f} | {ape:,.0f} | {cpu_ticks:,} |"
            )

    lines.append("\n\n*CPU/alloc/heap profiles and pprof diffs available as workflow artifacts.*")

    return "\n".join(lines), gh_bench


def build_gh_bench_full(results):
    """Build comprehensive gh-bench.json with all metrics for the dashboard.

    Produces two files:
    - gh-bench-bigger.json: metrics where higher is better (EPS, docs/sec)
    - gh-bench-smaller.json: metrics where lower is better (alloc/event, bytes/event, heap)
    """
    bigger = []   # EPS, throughput
    smaller = []  # allocs, memory, bytes

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
        prefix = f"{scenario} ({cpu} CPU)"

        # Bigger is better
        bigger.append({
            "name": f"{prefix} EPS",
            "unit": "events/sec",
            "value": pr_avg,
            "extra": f"base={base_avg} delta={sign}{delta}%",
        })

        # Extract per-event metrics from last PR run
        pr_runs = r.get("pr_runs", [])
        base_runs = r.get("base_runs", [])
        if pr_runs:
            last_pr = pr_runs[-1]
            last_base = base_runs[-1] if base_runs else {}

            bigger.append({
                "name": f"{prefix} mock docs/sec",
                "unit": "docs/sec",
                "value": int(last_pr.get("mock_docs_per_sec", 0)),
            })

            # Smaller is better
            pr_ape = last_pr.get("alloc_per_event", 0)
            base_ape = last_base.get("alloc_per_event", 0)
            smaller.append({
                "name": f"{prefix} alloc/event",
                "unit": "bytes",
                "value": int(pr_ape),
                "extra": f"base={int(base_ape)}" if base_ape else "",
            })

            pr_bpe = last_pr.get("bytes_per_event", 0)
            base_bpe = last_base.get("bytes_per_event", 0)
            smaller.append({
                "name": f"{prefix} bytes/event",
                "unit": "bytes",
                "value": int(pr_bpe),
                "extra": f"base={int(base_bpe)}" if base_bpe else "",
            })

            smaller.append({
                "name": f"{prefix} heap MB",
                "unit": "MB",
                "value": round(last_pr.get("memory_alloc_mb", 0), 1),
            })

    return bigger, smaller


def generate_pprof_diffs(results_dir):
    """Generate pprof diff commands and attempt to create text diffs."""
    results_path = Path(results_dir)
    diff_commands = []

    for subdir in sorted(results_path.iterdir()):
        if not subdir.is_dir():
            continue
        base_allocs = subdir / "base-allocs.pprof"
        pr_allocs = subdir / "pr-allocs.pprof"
        base_cpu = subdir / "base-cpu.pprof"
        pr_cpu = subdir / "pr-cpu.pprof"

        if base_allocs.exists() and pr_allocs.exists():
            diff_commands.append(
                f"go tool pprof -diff_base {base_allocs} {pr_allocs}"
            )
            # Try to generate text diff
            diff_file = subdir / "allocs-diff.txt"
            try:
                import subprocess
                result = subprocess.run(
                    ["go", "tool", "pprof", "-text", "-diff_base",
                     str(base_allocs), str(pr_allocs)],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    diff_file.write_text(result.stdout)
            except Exception:
                pass

        if base_cpu.exists() and pr_cpu.exists():
            diff_commands.append(
                f"go tool pprof -diff_base {base_cpu} {pr_cpu}"
            )
            diff_file = subdir / "cpu-diff.txt"
            try:
                import subprocess
                result = subprocess.run(
                    ["go", "tool", "pprof", "-text", "-diff_base",
                     str(base_cpu), str(pr_cpu)],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    diff_file.write_text(result.stdout)
            except Exception:
                pass

    return diff_commands


def main():
    args = parse_args()
    results = load_results(args.results_dir)

    if not results:
        print("WARNING: no results found", file=sys.stderr)

    md, _ = generate_summary(results, args)
    print(md)

    with open("summary.md", "w") as f:
        f.write(md)

    # Generate comprehensive dashboard data
    bigger, smaller = build_gh_bench_full(results)
    with open("gh-bench-bigger.json", "w") as f:
        json.dump(bigger, f, indent=2)
    with open("gh-bench-smaller.json", "w") as f:
        json.dump(smaller, f, indent=2)
    # Also write combined for backwards compat
    with open("gh-bench.json", "w") as f:
        json.dump(bigger, f, indent=2)

    # Generate pprof diffs
    diff_cmds = generate_pprof_diffs(args.results_dir)
    if diff_cmds:
        print("\nPprof diff commands:", file=sys.stderr)
        for cmd in diff_cmds:
            print(f"  {cmd}", file=sys.stderr)

    print(f"\nWrote summary.md, gh-bench-bigger.json, gh-bench-smaller.json", file=sys.stderr)


if __name__ == "__main__":
    main()
