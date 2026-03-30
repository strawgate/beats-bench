"""CLI entry points for beats-bench."""

from __future__ import annotations

import argparse
import json
import os
import sys


def _cmd_run_one(args: argparse.Namespace) -> None:
    from beats_bench.runner import run_one

    result = run_one(
        binary_path=args.binary,
        config_path=args.config,
        mock_es_path=args.mock_es,
        cpus=args.cpus,
        measure_seconds=args.measure,
        label=args.label,
    )
    print(json.dumps(result.to_dict()))


def _cmd_run_scenario(args: argparse.Namespace) -> None:
    from beats_bench.scenario import run_scenario

    run_scenario(
        base_bin=args.base_binary,
        pr_bin=args.pr_binary,
        config=args.config,
        mock_es=args.mock_es,
        cpus=args.cpus,
        measure=args.measure,
        runs=args.runs,
        output_dir=args.output_dir,
    )


def _cmd_summarize(args: argparse.Namespace) -> None:
    from beats_bench.summarize import SummarizeArgs, summarize

    summarize(
        SummarizeArgs(
            results_dir=args.results_dir,
            base_ref=args.base_ref,
            pr_ref=args.pr_ref,
            base_repo=args.base_repo,
            pr_repo=args.pr_repo,
            runs_per_scenario=args.runs_per_scenario,
            measure_seconds=args.measure_seconds,
        )
    )


def _cmd_local_run(args: argparse.Namespace) -> None:
    import subprocess

    # Try to find bench root by looking for scripts/build.sh
    # Walk up from the current working directory
    bench_root = os.getcwd()
    build_script = os.path.join(bench_root, "scripts", "build.sh")
    if not os.path.exists(build_script):
        print(
            "ERROR: scripts/build.sh not found. Run from the beats-bench repo root.",
            file=sys.stderr,
        )
        sys.exit(1)

    base_repo = os.environ.get("BASE_REPO", "https://github.com/elastic/beats.git")
    pr_repo = os.environ.get("PR_REPO", base_repo)

    print("==========================================")
    print("  Local Filebeat Benchmark")
    print("==========================================")
    print(f"  Base: {args.base_ref} @ {base_repo}")
    print(f"  PR:   {args.pr_ref} @ {pr_repo}")
    print(f"  Scenario: {args.scenario}")
    print(f"  CPUs: {args.cpus}, Runs: {args.runs}, Measure: {args.measure}s")
    print()

    # Build both binaries
    subprocess.run(
        [build_script, base_repo, args.base_ref, os.path.join(bench_root, "bin", "base")],
        check=True,
    )
    subprocess.run(
        [build_script, pr_repo, args.pr_ref, os.path.join(bench_root, "bin", "pr")],
        check=True,
    )

    # Prepare config
    config = os.path.join(bench_root, "pipelines", f"{args.scenario}.yml")
    if not os.path.exists(config):
        print(f"ERROR: Pipeline config not found: {config}", file=sys.stderr)
        sys.exit(1)

    from beats_bench.scenario import run_scenario

    output_dir = os.path.join(bench_root, "results", f"{args.scenario}-{args.cpus}cpu")
    run_scenario(
        base_bin=os.path.join(bench_root, "bin", "base", "filebeat"),
        pr_bin=os.path.join(bench_root, "bin", "pr", "filebeat"),
        config=config,
        mock_es=os.path.join(bench_root, "bin", "mock-es"),
        cpus=args.cpus,
        measure=args.measure,
        runs=args.runs,
        output_dir=output_dir,
    )

    print(f"\nResults: {output_dir}/")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(prog="beats-bench", description="Filebeat pipeline benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run-one
    p_one = subparsers.add_parser("run-one", help="Run one benchmark iteration")
    p_one.add_argument("--binary", required=True, help="Path to filebeat binary")
    p_one.add_argument("--config", required=True, help="Path to pipeline config")
    p_one.add_argument("--mock-es", required=True, help="Path to mock-es binary")
    p_one.add_argument("--cpus", default="1.0", help="CPU limit for Docker")
    p_one.add_argument("--measure", type=int, default=20, help="Measurement seconds")
    p_one.add_argument("--label", default="test", help="Label for this run")
    p_one.set_defaults(func=_cmd_run_one)

    # run-scenario
    p_scenario = subparsers.add_parser("run-scenario", help="Run full benchmark scenario")
    p_scenario.add_argument("--base-binary", required=True, help="Path to base filebeat binary")
    p_scenario.add_argument("--pr-binary", required=True, help="Path to PR filebeat binary")
    p_scenario.add_argument("--config", required=True, help="Path to pipeline config")
    p_scenario.add_argument("--mock-es", required=True, help="Path to mock-es binary")
    p_scenario.add_argument("--cpus", default="1.0", help="CPU limit for Docker")
    p_scenario.add_argument("--measure", type=int, default=20, help="Measurement seconds")
    p_scenario.add_argument("--runs", type=int, default=3, help="Number of measurement runs")
    p_scenario.add_argument("--output-dir", required=True, help="Output directory")
    p_scenario.set_defaults(func=_cmd_run_scenario)

    # summarize
    p_summarize = subparsers.add_parser("summarize", help="Generate summary from results")
    p_summarize.add_argument("--results-dir", required=True, help="Path to all-results directory")
    p_summarize.add_argument("--base-ref", required=True, help="Base git ref")
    p_summarize.add_argument("--pr-ref", required=True, help="PR git ref")
    p_summarize.add_argument("--base-repo", required=True, help="Base repo (owner/repo)")
    p_summarize.add_argument("--pr-repo", required=True, help="PR repo (owner/repo)")
    p_summarize.add_argument("--runs-per-scenario", type=int, required=True)
    p_summarize.add_argument("--measure-seconds", type=int, required=True)
    p_summarize.set_defaults(func=_cmd_summarize)

    # local-run
    p_local = subparsers.add_parser("local-run", help="Build and benchmark two refs locally")
    p_local.add_argument("--base-ref", default="main", help="Base ref")
    p_local.add_argument("--pr-ref", default="main", help="PR ref")
    p_local.add_argument("--scenario", default="full-agent-dissect", help="Pipeline scenario")
    p_local.add_argument("--cpus", default="1.0", help="CPU limit")
    p_local.add_argument("--runs", type=int, default=3, help="Number of runs")
    p_local.add_argument("--measure", type=int, default=20, help="Measurement seconds")
    p_local.set_defaults(func=_cmd_local_run)

    parsed = parser.parse_args()
    parsed.func(parsed)


if __name__ == "__main__":
    main()
