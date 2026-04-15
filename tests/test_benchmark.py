"""Tests for benchmark module — single-binary runner and benchmark-action output."""

from __future__ import annotations

import json

from beats_bench.benchmark import _to_benchmark_entries
from beats_bench.runner import RunResult
from beats_bench.stats import FilebeatStats, MockEsStats


def _make_result(
    eps: int = 7500,
    events: int = 150000,
    measure_sec: int = 20,
    memory_alloc: int = 15728640,
    memory_rss: int = 57671680,
    memory_total: int = 1468006400,
    bytes_received: int = 72000000,
) -> RunResult:
    fb = FilebeatStats(
        events_total=200000,
        events_acked=events,
        output_acked=events,
        output_failed=0,
        output_batches=3000,
        memory_alloc=memory_alloc,
        memory_rss=memory_rss,
        memory_total=memory_total,
        gc_next=25165824,
        goroutines=40,
        cpu_ticks=42000,
    )
    mock = MockEsStats(
        docs_ingested=events,
        batches=3000,
        bytes_received=bytes_received,
        avg_batch_size=50.0,
        docs_per_sec=float(eps),
    )
    return RunResult(
        label="measurement",
        eps=eps,
        events=events,
        measure_sec=measure_sec,
        fb_stats=fb,
        mock_stats=mock,
    )


class TestToBenchmarkEntries:
    def test_produces_eps_entry(self):
        results = [_make_result(eps=7500), _make_result(eps=7600)]
        entries = _to_benchmark_entries(results, "full-agent-dissect", "1.0")

        eps_entry = next(e for e in entries if e["unit"] == "events/s")
        assert eps_entry["name"] == "full-agent-dissect (1.0 CPU)"
        assert eps_entry["value"] == 7550.0  # median of [7500, 7600]

    def test_produces_alloc_per_event_entry(self):
        results = [_make_result(), _make_result()]
        entries = _to_benchmark_entries(results, "passthrough", "0.5")

        alloc_entry = next(e for e in entries if "alloc_per_event" in e["name"])
        assert alloc_entry["unit"] == "bytes/event"
        assert alloc_entry["value"] > 0

    def test_produces_memory_entries(self):
        results = [_make_result()]
        entries = _to_benchmark_entries(results, "passthrough", "1.0")

        names = {e["name"] for e in entries}
        assert "passthrough (1.0 CPU) memory_rss" in names
        assert "passthrough (1.0 CPU) memory_alloc" in names

    def test_empty_results(self):
        entries = _to_benchmark_entries([], "passthrough", "1.0")
        assert entries == []

    def test_single_run_uses_value_directly(self):
        results = [_make_result(eps=8000)]
        entries = _to_benchmark_entries(results, "passthrough", "1.0")

        eps_entry = next(e for e in entries if e["unit"] == "events/s")
        assert eps_entry["value"] == 8000.0

    def test_median_odd_count(self):
        results = [_make_result(eps=7000), _make_result(eps=7500), _make_result(eps=8000)]
        entries = _to_benchmark_entries(results, "test", "1.0")

        eps_entry = next(e for e in entries if e["unit"] == "events/s")
        assert eps_entry["value"] == 7500.0

    def test_entries_are_json_serializable(self):
        results = [_make_result()]
        entries = _to_benchmark_entries(results, "test-scenario", "0.5")
        json.dumps(entries)

    def test_skips_zero_metrics(self):
        results = [_make_result(memory_alloc=0, memory_rss=0, memory_total=0)]
        entries = _to_benchmark_entries(results, "test", "1.0")

        names = {e["name"] for e in entries}
        assert "test (1.0 CPU) memory_rss" not in names
        assert "test (1.0 CPU) memory_alloc" not in names
