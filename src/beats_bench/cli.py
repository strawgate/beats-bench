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


def _cmd_run_benchmark(args: argparse.Namespace) -> None:
    from beats_bench.benchmark import run_benchmark

    run_benchmark(
        binary=args.binary,
        config=args.config,
        mock_es=args.mock_es,
        cpus=args.cpus,
        measure=args.measure,
        runs=args.runs,
        output_dir=args.output_dir,
        scenario_name=getattr(args, "scenario", None),
        collect_pprof=not args.no_pprof,
    )


def _cmd_local_run(args: argparse.Namespace) -> None:
    import subprocess

    bench_root = os.getcwd()
    build_script = os.path.join(bench_root, "scripts", "build.sh")
    if not os.path.exists(build_script):
        print(
            "ERROR: scripts/build.sh not found. Run from the beats-bench repo root.",
            file=sys.stderr,
        )
        sys.exit(1)

    beats_repo = os.environ.get("BEATS_REPO", "https://github.com/elastic/beats.git")

    print("==========================================")
    print("  Local Filebeat Benchmark")
    print("==========================================")
    print(f"  Ref:      {args.ref} @ {beats_repo}")
    print(f"  Scenario: {args.scenario}")
    print(f"  CPUs: {args.cpus}, Runs: {args.runs}, Measure: {args.measure}s")
    print()

    # Build binary
    bin_dir = os.path.join(bench_root, "bin", "bench")
    subprocess.run(
        [build_script, beats_repo, args.ref, bin_dir],
        check=True,
    )

    config = os.path.join(bench_root, "pipelines", f"{args.scenario}.yml")
    if not os.path.exists(config):
        print(f"ERROR: Pipeline config not found: {config}", file=sys.stderr)
        sys.exit(1)

    from beats_bench.benchmark import run_benchmark

    output_dir = os.path.join(bench_root, "results", f"{args.scenario}-{args.cpus}cpu")
    run_benchmark(
        binary=os.path.join(bin_dir, "filebeat"),
        config=config,
        mock_es=os.path.join(bench_root, "bin", "mock-es"),
        cpus=args.cpus,
        measure=args.measure,
        runs=args.runs,
        output_dir=output_dir,
        scenario_name=args.scenario,
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

    # run-benchmark (replaces run-scenario)
    p_bench = subparsers.add_parser("run-benchmark", help="Run full benchmark (warmup + N runs)")
    p_bench.add_argument("--binary", required=True, help="Path to filebeat binary")
    p_bench.add_argument("--config", required=True, help="Path to pipeline config")
    p_bench.add_argument("--mock-es", required=True, help="Path to mock-es binary")
    p_bench.add_argument("--cpus", default="1.0", help="CPU limit for Docker")
    p_bench.add_argument("--measure", type=int, default=20, help="Measurement seconds")
    p_bench.add_argument("--runs", type=int, default=3, help="Number of measurement runs")
    p_bench.add_argument("--scenario", default=None, help="Scenario name")
    p_bench.add_argument("--output-dir", required=True, help="Output directory")
    p_bench.add_argument("--no-pprof", action="store_true", help="Skip profile collection")
    p_bench.set_defaults(func=_cmd_run_benchmark)

    # local-run
    p_local = subparsers.add_parser("local-run", help="Build and benchmark a ref locally")
    p_local.add_argument("--ref", default="main", help="Git ref to benchmark")
    p_local.add_argument("--scenario", default="full-agent-dissect", help="Pipeline scenario")
    p_local.add_argument("--cpus", default="1.0", help="CPU limit")
    p_local.add_argument("--runs", type=int, default=3, help="Number of runs")
    p_local.add_argument("--measure", type=int, default=20, help="Measurement seconds")
    p_local.set_defaults(func=_cmd_local_run)

    parsed = parser.parse_args()
    parsed.func(parsed)


if __name__ == "__main__":
    main()
