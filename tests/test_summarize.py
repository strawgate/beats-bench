"""Tests for markdown generation, dashboard data, and site building."""

from __future__ import annotations

import json

from beats_bench.summarize import (
    SummarizeArgs,
    build_site,
    generate_dashboard_data,
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


class TestBuildSite:
    def test_site_contains_expected_files(self, sample_results_dir, tmp_path):
        results = load_results(str(sample_results_dir))
        args = _make_args()
        dashboard = generate_dashboard_data(results, args, "12345")

        output_dir = str(tmp_path / "_site")
        build_site(output_dir, "", dashboard)

        from pathlib import Path

        site = Path(output_dir)
        assert (site / "index.html").exists()
        assert (site / "run.html").exists()
        assert (site / "style.css").exists()
        assert (site / "data" / "index.json").exists()
        assert (site / "data" / "runs" / "12345.json").exists()

        # Verify index.json structure
        idx = json.loads((site / "data" / "index.json").read_text())
        assert len(idx["runs"]) == 1
        assert idx["runs"][0]["id"] == "12345"

        # Verify run JSON is valid and contains run_data
        run_json = json.loads((site / "data" / "runs" / "12345.json").read_text())
        assert "run_data" in run_json
        assert run_json["run_data"]["id"] == "12345"

    def test_site_merges_existing_data(self, sample_results_dir, tmp_path):
        results = load_results(str(sample_results_dir))
        args = _make_args()

        # Create existing data directory with a prior run
        existing = tmp_path / "existing"
        existing.mkdir()
        runs_dir = existing / "runs"
        runs_dir.mkdir()
        old_entry = {
            "id": "99999",
            "date": "2025-01-01T00:00:00Z",
            "base_ref": "main",
            "pr_ref": "old-branch",
            "base_repo": "elastic/beats",
            "pr_repo": "elastic/beats",
            "scenarios": ["passthrough"],
            "cpus": ["1.0"],
        }
        (existing / "index.json").write_text(json.dumps({"runs": [old_entry]}))
        (runs_dir / "99999.json").write_text(json.dumps({"run_data": {"id": "99999"}}))

        dashboard = generate_dashboard_data(results, args, "12345")
        output_dir = str(tmp_path / "_site")
        build_site(output_dir, str(existing), dashboard)

        from pathlib import Path

        site = Path(output_dir)
        idx = json.loads((site / "data" / "index.json").read_text())
        # Should have both old and new runs
        assert len(idx["runs"]) == 2
        ids = [r["id"] for r in idx["runs"]]
        assert "12345" in ids
        assert "99999" in ids

        # Both run JSONs should exist
        assert (site / "data" / "runs" / "12345.json").exists()
        assert (site / "data" / "runs" / "99999.json").exists()

    def test_dashboard_data_json_serializable(self, sample_results_dir):
        results = load_results(str(sample_results_dir))
        args = _make_args()
        dashboard = generate_dashboard_data(results, args, "12345")

        # Must be JSON-serializable
        json.dumps(dashboard)
        assert "run_data" in dashboard
        assert "index_entry" in dashboard
