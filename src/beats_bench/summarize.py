"""Generate markdown + dashboard JSON from benchmark results, and build the static site."""

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
    existing_data: str = ""
    output_dir: str = ""
    run_id: str = ""
    pr_number: str = ""
    run_type: str = "pr"
    commit_sha: str = ""
    pr_repo_owner: str = ""


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


def _compute_summary(scenarios: dict) -> dict:
    """Compute summary stats (base_avg, pr_avg, delta_pct) for each scenario/cpu pair."""
    summary: dict = {}
    for scenario, cpu_data in scenarios.items():
        summary[scenario] = {}
        for cpu, metrics in cpu_data.items():
            base_vals = metrics.get("base_eps", [])
            pr_vals = metrics.get("pr_eps", [])
            base_avg = sum(base_vals) // len(base_vals) if base_vals else 0
            pr_avg = sum(pr_vals) // len(pr_vals) if pr_vals else 0
            delta_pct = ((pr_avg - base_avg) * 100 / base_avg) if base_avg > 0 else 0.0
            summary[scenario][cpu] = {
                "base_avg": base_avg,
                "pr_avg": pr_avg,
                "delta_pct": round(delta_pct, 1),
            }
    return summary


def fetch_pr_metadata(pr_numbers: list[int], repo: str) -> dict[int, dict]:
    """Call ``gh pr view`` for each PR number and return parsed metadata.

    Returns a dict keyed by PR number.  On any failure the entry is an empty
    dict so callers can continue gracefully.
    """
    result: dict[int, dict] = {}
    for num in pr_numbers:
        try:
            proc = subprocess.run(
                [
                    "gh",
                    "pr",
                    "view",
                    str(num),
                    "--repo",
                    repo,
                    "--json",
                    "title,author,state,url,number",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if proc.returncode == 0:
                data = json.loads(proc.stdout)
                result[num] = data
            else:
                result[num] = {}
        except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
            result[num] = {}
    return result


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

    summary = _compute_summary(scenarios)

    run_data = {
        "id": run_id,
        "date": date,
        "base_ref": args.base_ref,
        "pr_ref": args.pr_ref,
        "base_repo": args.base_repo,
        "pr_repo": args.pr_repo,
        "type": args.run_type,
        "pr_number": int(args.pr_number) if args.pr_number else None,
        "commit_sha": args.commit_sha,
        "summary": summary,
        "scenarios": scenarios,
    }

    index_entry = {
        "id": run_id,
        "date": date,
        "base_ref": args.base_ref,
        "pr_ref": args.pr_ref,
        "base_repo": args.base_repo,
        "pr_repo": args.pr_repo,
        "type": args.run_type,
        "pr_number": int(args.pr_number) if args.pr_number else None,
        "commit_sha": args.commit_sha,
        "summary": summary,
        "scenarios": scenario_names,
        "cpus": sorted(cpu_set),
    }

    return {"run_data": run_data, "index_entry": index_entry}


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


def build_site(output_dir: str, existing_data: str, dashboard: dict) -> None:
    """Build the full static site in output_dir.

    Generates:
      - index.html (overview)
      - pr/{N}/index.html for each PR
      - run/{id}/index.html for each run
      - style.css
      - data/index.json + data/runs/{id}.json
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Load existing index and runs
    existing_path = Path(existing_data) if existing_data else Path()
    existing_index: dict = {"runs": []}
    existing_runs: dict[str, dict] = {}

    if existing_data:
        idx_file = existing_path / "index.json"
        if idx_file.exists():
            existing_index = json.loads(idx_file.read_text())
        runs_dir = existing_path / "runs"
        if runs_dir.exists():
            for f in runs_dir.iterdir():
                if f.suffix == ".json":
                    existing_runs[f.stem] = json.loads(f.read_text())

    # Add the new run
    new_entry = dashboard["index_entry"]
    new_run_data = dashboard["run_data"]
    run_id = new_entry["id"]

    # Remove any existing entry with same id (re-run case)
    existing_index["runs"] = [r for r in existing_index["runs"] if r["id"] != run_id]
    existing_index["runs"].append(new_entry)
    existing_index["runs"].sort(key=lambda r: r["date"], reverse=True)

    existing_runs[run_id] = {"run_data": new_run_data}

    # Write data directory
    data_dir = out / "data"
    runs_out = data_dir / "runs"
    runs_out.mkdir(parents=True, exist_ok=True)

    (data_dir / "index.json").write_text(json.dumps(existing_index, indent=2))
    for rid, rdata in existing_runs.items():
        (runs_out / f"{rid}.json").write_text(json.dumps(rdata, indent=2))

    # HTML is generated by the Preact dashboard (dashboard/ directory),
    # which fetches data at runtime from the bench-data branch.
    # This function only writes the data/ files.


def summarize(args: SummarizeArgs) -> tuple[str, list[dict]]:
    """Main summarize entry point. Returns (markdown, gh_bench)."""
    results = load_results(args.results_dir)

    if not results:
        print("WARNING: no results found", file=sys.stderr)

    md, gh_bench = generate_summary(results, args)
    print(md)

    with open("summary.md", "w") as f:
        f.write(md)

    # Generate custom dashboard data
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID", "local")
    dashboard = generate_dashboard_data(results, args, run_id)
    with open("dashboard-data.json", "w") as f:
        json.dump(dashboard, f, indent=2)

    # Build static site if output_dir is specified
    if args.output_dir:
        build_site(args.output_dir, args.existing_data, dashboard)
        print(f"\nBuilt static site in {args.output_dir}", file=sys.stderr)

    diff_cmds = generate_pprof_diffs(args.results_dir)
    if diff_cmds:
        print("\nPprof diff commands:", file=sys.stderr)
        for cmd in diff_cmds:
            print(f"  {cmd}", file=sys.stderr)

    print(
        "\nWrote summary.md, dashboard-data.json",
        file=sys.stderr,
    )

    return md, gh_bench
