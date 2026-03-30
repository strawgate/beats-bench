"""Tests for RunResult dataclass and derived metrics."""

from __future__ import annotations

from beats_bench.runner import RunResult, Sample
from beats_bench.stats import FilebeatStats, MockEsStats


def _make_result(
    events: int = 150000,
    measure_sec: int = 20,
    memory_total: int = 1572864000,
    bytes_received: int = 75000000,
) -> RunResult:
    fb = FilebeatStats(
        events_total=200000,
        events_acked=150000,
        output_acked=150000,
        output_failed=5,
        output_batches=3000,
        memory_alloc=18743296,
        memory_rss=62914560,
        memory_total=memory_total,
        gc_next=25165824,
        goroutines=42,
        cpu_ticks=48230,
    )
    mock = MockEsStats(
        docs_ingested=150000,
        batches=3000,
        bytes_received=bytes_received,
        avg_batch_size=50.0,
        docs_per_sec=7500.0,
    )
    return RunResult(
        label="test",
        eps=events // measure_sec,
        events=events,
        measure_sec=measure_sec,
        fb_stats=fb,
        mock_stats=mock,
        samples=[
            Sample(elapsed_sec=5, events=50000, mem_bytes=18000000, rss_bytes=60000000),
            Sample(elapsed_sec=10, events=100000, mem_bytes=18500000, rss_bytes=61000000),
        ],
    )


class TestRunResult:
    def test_eps_computation(self):
        result = _make_result(events=150000, measure_sec=20)
        assert result.eps == 7500

    def test_bytes_per_event(self):
        result = _make_result(events=150000, bytes_received=75000000)
        assert result.bytes_per_event == round(75000000 / 150000)

    def test_alloc_per_event(self):
        result = _make_result(events=150000, memory_total=1572864000)
        assert result.alloc_per_event == round(1572864000 / 150000)

    def test_bytes_per_event_zero_events(self):
        result = _make_result(events=0, measure_sec=20)
        # eps will be 0//20 = 0
        result_zero = RunResult(
            label="test",
            eps=0,
            events=0,
            measure_sec=20,
            fb_stats=result.fb_stats,
            mock_stats=result.mock_stats,
        )
        assert result_zero.bytes_per_event == 0.0
        assert result_zero.alloc_per_event == 0.0

    def test_memory_properties(self):
        result = _make_result()
        assert result.memory_alloc_mb == result.fb_stats.memory_alloc_mb
        assert result.memory_rss_mb == result.fb_stats.memory_rss_mb
        assert result.gc_next_mb == result.fb_stats.gc_next_mb
        assert result.mock_bytes_mb == result.mock_stats.bytes_received_mb

    def test_to_dict_shape(self):
        result = _make_result()
        d = result.to_dict()

        assert d["label"] == "test"
        assert d["eps"] == 7500
        assert d["events"] == 150000
        assert d["measure_sec"] == 20
        assert d["memory_alloc_mb"] == result.memory_alloc_mb
        assert d["goroutines"] == 42
        assert d["mock_docs"] == 150000
        assert d["bytes_per_event"] == result.bytes_per_event
        assert d["alloc_per_event"] == result.alloc_per_event
        assert len(d["samples"]) == 2
        assert d["samples"][0]["elapsed_sec"] == 5

    def test_to_dict_all_keys_present(self):
        result = _make_result()
        d = result.to_dict()
        expected_keys = {
            "label",
            "eps",
            "events",
            "measure_sec",
            "memory_alloc_mb",
            "memory_rss_mb",
            "gc_next_mb",
            "goroutines",
            "mock_docs",
            "mock_batches",
            "mock_bytes_mb",
            "mock_avg_batch",
            "mock_docs_per_sec",
            "output_acked",
            "output_failed",
            "output_batches",
            "memory_total_mb",
            "cpu_ticks",
            "bytes_per_event",
            "alloc_per_event",
            "samples",
        }
        assert set(d.keys()) == expected_keys
