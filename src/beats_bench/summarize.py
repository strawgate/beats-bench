"""Generate markdown + dashboard JSON from benchmark results (replaces scripts/summarize.py)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path


@dataclass
class SummarizeArgs:
    """Arguments for summarize."""

    results_dir: str
    base_ref: str
    pr_ref: str
    base_repo: str
    pr_repo: str
    runs_per_scenario: int
    measure_seconds: int


def load_results(results_dir: str) -> list[dict]:
    """Load all scenario results from the results directory."""
    results: list[dict] = []
    results_path = Path(results_dir)

    if not results_path.exists():
        print(f"ERROR: results directory {results_dir} does not exist", file=sys.stderr)
        return []

    for subdir in sorted(results_path.iterdir()):
        if not subdir.is_dir():
            continue

        results_txt = subdir / "results.txt"
        if not results_txt.exists():
            continue

        data: dict = {"dir": subdir.name}

        # Parse results.txt (key=value)
        for line in results_txt.read_text().splitlines():
            if "=" in line:
                k, v = line.strip().split("=", 1)
                data[k] = v

        # Parse runs.jsonl for detailed per-run data
        runs_jsonl = subdir / "runs.jsonl"
        if runs_jsonl.exists():
            base_runs: list[dict] = []
            pr_runs: list[dict] = []
            for raw_line in runs_jsonl.read_text().splitlines():
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    run = json.loads(stripped)
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


def generate_summary(results: list[dict], args: SummarizeArgs) -> tuple[str, list[dict]]:
    """Generate the summary markdown and gh-bench.json data."""
    lines: list[str] = []
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

    gh_bench: list[dict] = []
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
        gh_bench.append(
            {
                "name": f"{scenario} ({cpu} CPU)",
                "unit": "events/sec",
                "value": pr_avg,
                "extra": f"base={base_avg} delta={sign}{delta}%",
            }
        )

    # ---- Resource usage table (from runs.jsonl) ----
    lines.append("\n### Resource usage (from final measurement run)\n")
    lines.append(
        "| Scenario | CPU | Variant | Alloc (MB) | RSS (MB) | GC next (MB) | Goroutines |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|")

    for r in results:
        scenario = r["scenario"]
        cpu = r["cpu"]
        for label, runs_key in [("base", "base_runs"), ("pr", "pr_runs")]:
            runs = r.get(runs_key, [])
            if not runs:
                continue
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
    lines.append(
        "| Scenario | CPU | Variant | Docs | Batches | Avg batch | Bytes (MB) | Docs/sec |"
    )
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
                f"| {scenario} | {cpu} | {label} | {bpe:,.0f} | {ape:,.0f} | {cpu_ticks:,} |"
            )

    lines.append("\n\n*CPU/alloc/heap profiles and pprof diffs available as workflow artifacts.*")

    return "\n".join(lines), gh_bench


def build_gh_bench_full(results: list[dict]) -> tuple[list[dict], list[dict]]:
    """Build comprehensive gh-bench.json with all metrics for the dashboard.

    Returns:
        Tuple of (bigger_is_better, smaller_is_better) benchmark lists.
    """
    bigger: list[dict] = []
    smaller: list[dict] = []

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

        bigger.append(
            {
                "name": f"{prefix} EPS",
                "unit": "events/sec",
                "value": pr_avg,
                "extra": f"base={base_avg} delta={sign}{delta}%",
            }
        )

        pr_runs = r.get("pr_runs", [])
        base_runs = r.get("base_runs", [])
        if pr_runs:
            last_pr = pr_runs[-1]
            last_base = base_runs[-1] if base_runs else {}

            bigger.append(
                {
                    "name": f"{prefix} mock docs/sec",
                    "unit": "docs/sec",
                    "value": int(last_pr.get("mock_docs_per_sec", 0)),
                }
            )

            pr_ape = last_pr.get("alloc_per_event", 0)
            base_ape = last_base.get("alloc_per_event", 0)
            smaller.append(
                {
                    "name": f"{prefix} alloc/event",
                    "unit": "bytes",
                    "value": int(pr_ape),
                    "extra": f"base={int(base_ape)}" if base_ape else "",
                }
            )

            pr_bpe = last_pr.get("bytes_per_event", 0)
            base_bpe = last_base.get("bytes_per_event", 0)
            smaller.append(
                {
                    "name": f"{prefix} bytes/event",
                    "unit": "bytes",
                    "value": int(pr_bpe),
                    "extra": f"base={int(base_bpe)}" if base_bpe else "",
                }
            )

            smaller.append(
                {
                    "name": f"{prefix} heap MB",
                    "unit": "MB",
                    "value": round(last_pr.get("memory_alloc_mb", 0), 1),
                }
            )

    return bigger, smaller


def generate_pprof_diffs(results_dir: str) -> list[str]:
    """Generate pprof diff commands and attempt to create text diffs."""
    results_path = Path(results_dir)
    diff_commands: list[str] = []

    for subdir in sorted(results_path.iterdir()):
        if not subdir.is_dir():
            continue

        for profile_type, diff_name in [("allocs", "allocs-diff"), ("cpu", "cpu-diff")]:
            base_profile = subdir / f"base-{profile_type}.pprof"
            pr_profile = subdir / f"pr-{profile_type}.pprof"

            if not (base_profile.exists() and pr_profile.exists()):
                continue

            diff_commands.append(f"go tool pprof -diff_base {base_profile} {pr_profile}")

            diff_file = subdir / f"{diff_name}.txt"
            try:
                result = subprocess.run(
                    [
                        "go",
                        "tool",
                        "pprof",
                        "-text",
                        "-diff_base",
                        str(base_profile),
                        str(pr_profile),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                if result.returncode == 0:
                    diff_file.write_text(result.stdout)
            except (subprocess.SubprocessError, OSError):
                pass

    return diff_commands


def generate_dashboard_data(results: list[dict], args: SummarizeArgs, run_id: str) -> dict:
    """Generate structured JSON for the custom GitHub Pages dashboard.

    Returns a dict suitable for writing to data/runs/{run-id}.json on gh-pages.
    """
    from datetime import datetime

    date = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    scenarios: dict = {}
    scenario_names: list[str] = []
    cpu_set: set[str] = set()

    for r in results:
        scenario = r["scenario"]
        cpu = r["cpu"]
        if scenario not in scenario_names:
            scenario_names.append(scenario)
        cpu_set.add(cpu)

        base_vals = [int(x) for x in r["base_eps"].split(",") if x]
        pr_vals = [int(x) for x in r["pr_eps"].split(",") if x]

        base_runs_raw = r.get("base_runs", [])
        pr_runs_raw = r.get("pr_runs", [])

        if scenario not in scenarios:
            scenarios[scenario] = {}
        scenarios[scenario][cpu] = {
            "base_eps": base_vals,
            "pr_eps": pr_vals,
            "base_runs": base_runs_raw,
            "pr_runs": pr_runs_raw,
        }

    run_data = {
        "id": run_id,
        "date": date,
        "base_ref": args.base_ref,
        "pr_ref": args.pr_ref,
        "base_repo": args.base_repo,
        "pr_repo": args.pr_repo,
        "scenarios": scenarios,
    }

    index_entry = {
        "id": run_id,
        "date": date,
        "base_ref": args.base_ref,
        "pr_ref": args.pr_ref,
        "base_repo": args.base_repo,
        "pr_repo": args.pr_repo,
        "scenarios": scenario_names,
        "cpus": sorted(cpu_set),
    }

    return {"run_data": run_data, "index_entry": index_entry}


def summarize(args: SummarizeArgs) -> tuple[str, list[dict]]:
    """Main summarize entry point. Returns (markdown, gh_bench)."""
    results = load_results(args.results_dir)

    if not results:
        print("WARNING: no results found", file=sys.stderr)

    md, gh_bench = generate_summary(results, args)
    print(md)

    with open("summary.md", "w") as f:
        f.write(md)

    bigger, smaller = build_gh_bench_full(results)
    with open("gh-bench-bigger.json", "w") as f:
        json.dump(bigger, f, indent=2)
    with open("gh-bench-smaller.json", "w") as f:
        json.dump(smaller, f, indent=2)
    with open("gh-bench.json", "w") as f:
        json.dump(bigger, f, indent=2)

    # Generate custom dashboard data
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    dashboard = generate_dashboard_data(results, args, run_id)
    with open("dashboard-data.json", "w") as f:
        json.dump(dashboard, f, indent=2)

    diff_cmds = generate_pprof_diffs(args.results_dir)
    if diff_cmds:
        print("\nPprof diff commands:", file=sys.stderr)
        for cmd in diff_cmds:
            print(f"  {cmd}", file=sys.stderr)

    print(
        "\nWrote summary.md, gh-bench-bigger.json, gh-bench-smaller.json, dashboard-data.json",
        file=sys.stderr,
    )

    return md, gh_bench
