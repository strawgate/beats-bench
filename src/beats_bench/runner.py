"""Run one benchmark iteration (replaces run-one.sh)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from beats_bench.docker import (
    ensure_network,
    fetch_json,
    reset_mock_es,
    start_filebeat,
    start_mock_es,
    stop_all,
    wait_for_endpoint,
)
from beats_bench.stats import (
    FilebeatStats,
    MockEsStats,
    parse_filebeat_stats,
    parse_mock_es_stats,
)

STATS_URL = "http://localhost:5066/stats"
MOCK_STATS_URL = "http://localhost:9200/_mock/stats"
MOCK_ROOT_URL = "http://localhost:9200/"


@dataclass(frozen=True)
class Sample:
    """A single time-series sample taken during measurement."""

    elapsed_sec: int
    events: int
    mem_bytes: int
    rss_bytes: int


@dataclass
class RunResult:
    """Result of a single benchmark run."""

    label: str
    eps: int
    events: int
    measure_sec: int
    fb_stats: FilebeatStats
    mock_stats: MockEsStats
    samples: list[Sample] = field(default_factory=list)

    @property
    def memory_alloc_mb(self) -> float:
        return self.fb_stats.memory_alloc_mb

    @property
    def memory_rss_mb(self) -> float:
        return self.fb_stats.memory_rss_mb

    @property
    def gc_next_mb(self) -> float:
        return self.fb_stats.gc_next_mb

    @property
    def memory_total_mb(self) -> float:
        return self.fb_stats.memory_total_mb

    @property
    def mock_bytes_mb(self) -> float:
        return self.mock_stats.bytes_received_mb

    @property
    def bytes_per_event(self) -> float:
        if self.events <= 0:
            return 0.0
        return round(self.mock_stats.bytes_received / self.events)

    @property
    def alloc_per_event(self) -> float:
        if self.events <= 0:
            return 0.0
        return round(self.fb_stats.memory_total / self.events)

    def to_dict(self) -> dict:
        """Serialize to the same JSON shape as the original bash script."""
        return {
            "label": self.label,
            "eps": self.eps,
            "events": self.events,
            "measure_sec": self.measure_sec,
            "memory_alloc_mb": self.memory_alloc_mb,
            "memory_rss_mb": self.memory_rss_mb,
            "gc_next_mb": self.gc_next_mb,
            "goroutines": self.fb_stats.goroutines,
            "mock_docs": self.mock_stats.docs_ingested,
            "mock_batches": self.mock_stats.batches,
            "mock_bytes_mb": self.mock_bytes_mb,
            "mock_avg_batch": self.mock_stats.avg_batch_size,
            "mock_docs_per_sec": self.mock_stats.docs_per_sec,
            "output_acked": self.fb_stats.output_acked,
            "output_failed": self.fb_stats.output_failed,
            "output_batches": self.fb_stats.output_batches,
            "memory_total_mb": self.memory_total_mb,
            "cpu_ticks": self.fb_stats.cpu_ticks,
            "bytes_per_event": self.bytes_per_event,
            "alloc_per_event": self.alloc_per_event,
            "samples": [
                {
                    "elapsed_sec": s.elapsed_sec,
                    "events": s.events,
                    "mem_bytes": s.mem_bytes,
                    "rss_bytes": s.rss_bytes,
                }
                for s in self.samples
            ],
        }


def _resolve_path(path: str) -> str:
    """Resolve a path to absolute for Docker volume mounts."""
    return os.path.abspath(path)


def _wait_for_events_acked(timeout: int = 60) -> None:
    """Wait until filebeat has acked at least one event (steady state)."""
    for _ in range(timeout):
        data = fetch_json(STATS_URL)
        fb = parse_filebeat_stats(data) if data else None
        if fb and fb.events_acked > 0:
            break
        time.sleep(1)
    # Let GC pacer stabilize after initial burst
    time.sleep(5)


def run_one(
    binary_path: str,
    config_path: str,
    mock_es_path: str,
    cpus: str,
    measure_seconds: int,
    label: str,
) -> RunResult:
    """Run one benchmark iteration and return structured results."""
    binary_path = _resolve_path(binary_path)
    config_path = _resolve_path(config_path)
    mock_es_path = _resolve_path(mock_es_path)

    # Ensure Docker network exists and clean up any leftovers
    ensure_network()
    stop_all()

    # Start mock-es
    start_mock_es(mock_es_path)
    if not wait_for_endpoint(MOCK_ROOT_URL):
        stop_all()
        msg = "mock-es did not start"
        raise RuntimeError(msg)

    # Reset mock-es stats
    reset_mock_es()

    # Start filebeat
    start_filebeat(binary_path, config_path, cpus)
    if not wait_for_endpoint(STATS_URL):
        stop_all()
        msg = "filebeat stats endpoint did not start"
        raise RuntimeError(msg)

    # Wait for steady state
    _wait_for_events_acked()

    # Reset mock-es counters so measurement stats start clean
    reset_mock_es()

    # Capture baseline events
    start_data = fetch_json(STATS_URL)
    start_fb = parse_filebeat_stats(start_data) if start_data else None
    start_events = start_fb.events_total if start_fb else 0

    # Sample every 5 seconds during measurement window
    sample_interval = 5
    elapsed = 0
    samples: list[Sample] = []
    while elapsed < measure_seconds:
        time.sleep(sample_interval)
        elapsed += sample_interval
        sample_data = fetch_json(STATS_URL)
        if sample_data:
            fb = parse_filebeat_stats(sample_data)
            samples.append(
                Sample(
                    elapsed_sec=elapsed,
                    events=fb.events_total,
                    mem_bytes=fb.memory_alloc,
                    rss_bytes=fb.memory_rss,
                )
            )

    # Collect final stats
    end_data = fetch_json(STATS_URL)
    fb_stats = parse_filebeat_stats(end_data) if end_data else parse_filebeat_stats({})
    end_events = fb_stats.events_total

    events = end_events - start_events
    eps = events // measure_seconds if measure_seconds > 0 else 0

    mock_data = fetch_json(MOCK_STATS_URL)
    mock_stats = parse_mock_es_stats(mock_data) if mock_data else parse_mock_es_stats({})

    # Clean up
    stop_all()

    return RunResult(
        label=label,
        eps=eps,
        events=events,
        measure_sec=measure_seconds,
        fb_stats=fb_stats,
        mock_stats=mock_stats,
        samples=samples,
    )
