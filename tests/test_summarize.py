"""Tests for markdown generation and gh-bench JSON generation."""

from __future__ import annotations

import json

from beats_bench.summarize import (
    SummarizeArgs,
    build_gh_bench_full,
    generate_summary,
    load_results,
)


def _make_args() -> SummarizeArgs:
    return SummarizeArgs(
        results_dir="unused",
        base_ref="main",
        pr_ref="feature-branch",
        base_repo="elastic/beats",
        pr_repo="elastic/beats",
        runs_per_scenario=3,
        measure_seconds=20,
    )


class TestLoadResults:
    def test_load_from_sample_dir(self, sample_results_dir):
        results = load_results(str(sample_results_dir))

        assert len(results) == 1
        r = results[0]
        assert r["scenario"] == "full-agent-dissect"
        assert r["cpu"] == "1.0"
        assert r["base_eps"] == "7000,7200,6800"
        assert r["pr_eps"] == "7500,7600,7400"
        assert len(r["base_runs"]) == 1
        assert len(r["pr_runs"]) == 1

    def test_load_nonexistent_dir(self):
        results = load_results("/nonexistent/path")
        assert results == []


class TestGenerateSummary:
    def test_markdown_contains_scenario(self, sample_results_dir):
        results = load_results(str(sample_results_dir))
        args = _make_args()
        md, _gh_bench = generate_summary(results, args)

        assert "full-agent-dissect" in md
        assert "main" in md
        assert "feature-branch" in md
        assert "Throughput" in md

    def test_markdown_has_tables(self, sample_results_dir):
        results = load_results(str(sample_results_dir))
        args = _make_args()
        md, _ = generate_summary(results, args)

        assert "| Scenario |" in md
        assert "Resource usage" in md
        assert "Mock-ES sink stats" in md
        assert "Per-event efficiency" in md

    def test_gh_bench_entries(self, sample_results_dir):
        results = load_results(str(sample_results_dir))
        args = _make_args()
        _, gh_bench = generate_summary(results, args)

        assert len(gh_bench) == 1
        entry = gh_bench[0]
        assert entry["name"] == "full-agent-dissect (1.0 CPU)"
        assert entry["unit"] == "events/sec"
        assert isinstance(entry["value"], int)

    def test_delta_computation(self, sample_results_dir):
        results = load_results(str(sample_results_dir))
        args = _make_args()
        md, _ = generate_summary(results, args)

        # base_avg = (7000+7200+6800)//3 = 7000
        # pr_avg = (7500+7600+7400)//3 = 7500
        # delta = (7500-7000)*100//7000 = 7%
        assert "+7%" in md


class TestBuildGhBenchFull:
    def test_bigger_and_smaller(self, sample_results_dir):
        results = load_results(str(sample_results_dir))
        bigger, smaller = build_gh_bench_full(results)

        # Should have EPS + mock docs/sec in bigger
        assert len(bigger) == 2
        eps_entry = bigger[0]
        assert "EPS" in eps_entry["name"]
        assert eps_entry["unit"] == "events/sec"

        # Should have alloc/event, bytes/event, heap MB in smaller
        assert len(smaller) == 3
        names = [s["name"] for s in smaller]
        assert any("alloc/event" in n for n in names)
        assert any("bytes/event" in n for n in names)
        assert any("heap MB" in n for n in names)

    def test_json_serializable(self, sample_results_dir):
        results = load_results(str(sample_results_dir))
        bigger, smaller = build_gh_bench_full(results)

        # Must be JSON-serializable for the workflow
        json.dumps(bigger)
        json.dumps(smaller)
