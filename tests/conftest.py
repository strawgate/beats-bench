"""Fixtures with sample stats JSON for tests."""

from __future__ import annotations

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
