"""Fixtures with sample stats JSON for tests."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def filebeat_stats_json() -> dict:
    """Sample filebeat /stats response from a real run."""
    return {
        "beat": {
            "cpu": {
                "total": {
                    "ticks": 48230,
                    "time": {"ms": 48230},
                },
            },
            "memstats": {
                "gc_next": 25165824,
                "memory_alloc": 18743296,
                "memory_total": 1572864000,
                "rss": 62914560,
            },
            "runtime": {
                "goroutines": 42,
            },
        },
        "libbeat": {
            "output": {
                "events": {
                    "acked": 150000,
                    "batches": 3000,
                    "failed": 5,
                },
            },
            "pipeline": {
                "events": {
                    "total": 155000,
                },
            },
        },
    }


@pytest.fixture
def mock_es_stats_json() -> dict:
    """Sample mock-es /_mock/stats response."""
    return {
        "docs_ingested": 150000,
        "batches": 3000,
        "bytes_received": 75000000,
        "avg_batch_size": 50.0,
        "docs_per_sec": 7500.0,
    }


@pytest.fixture
def sample_results_dir(tmp_path):
    """Create a sample results directory structure for summarize tests."""
    scenario_dir = tmp_path / "results-full-agent-dissect-1.0cpu"
    scenario_dir.mkdir()

    # results.txt
    (scenario_dir / "results.txt").write_text(
        "scenario=full-agent-dissect\ncpu=1.0\nbase_eps=7000,7200,6800\npr_eps=7500,7600,7400\n"
    )

    # runs.jsonl
    base_run = {
        "label": "base",
        "eps": 7000,
        "events": 140000,
        "measure_sec": 20,
        "memory_alloc_mb": 17.87,
        "memory_rss_mb": 60.0,
        "gc_next_mb": 24.0,
        "goroutines": 42,
        "mock_docs": 140000,
        "mock_batches": 2800,
        "mock_bytes_mb": 67.0,
        "mock_avg_batch": 50.0,
        "mock_docs_per_sec": 7000.0,
        "output_acked": 140000,
        "output_failed": 0,
        "output_batches": 2800,
        "memory_total_mb": 1500.0,
        "cpu_ticks": 45000,
        "bytes_per_event": 500,
        "alloc_per_event": 11200,
        "samples": [],
    }
    pr_run = {
        "label": "pr",
        "eps": 7500,
        "events": 150000,
        "measure_sec": 20,
        "memory_alloc_mb": 15.0,
        "memory_rss_mb": 55.0,
        "gc_next_mb": 22.0,
        "goroutines": 40,
        "mock_docs": 150000,
        "mock_batches": 3000,
        "mock_bytes_mb": 71.5,
        "mock_avg_batch": 50.0,
        "mock_docs_per_sec": 7500.0,
        "output_acked": 150000,
        "output_failed": 0,
        "output_batches": 3000,
        "memory_total_mb": 1400.0,
        "cpu_ticks": 42000,
        "bytes_per_event": 480,
        "alloc_per_event": 9800,
        "samples": [],
    }
    lines = [json.dumps(base_run), json.dumps(pr_run)]
    (scenario_dir / "runs.jsonl").write_text("\n".join(lines) + "\n")

    return tmp_path


@pytest.fixture
def sample_results_dir_with_pr(sample_results_dir):
    """Return sample_results_dir — caller should pass pr_number/type via args."""
    return sample_results_dir
