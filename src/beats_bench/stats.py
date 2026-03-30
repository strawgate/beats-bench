"""Pure functions for parsing stats JSON from filebeat and mock-es."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FilebeatStats:
    """Parsed stats from filebeat's /stats endpoint."""

    events_total: int
    events_acked: int
    output_acked: int
    output_failed: int
    output_batches: int
    memory_alloc: int
    memory_rss: int
    memory_total: int
    gc_next: int
    goroutines: int
    cpu_ticks: int

    @property
    def memory_alloc_mb(self) -> float:
        return round(self.memory_alloc / 1048576, 2)

    @property
    def memory_rss_mb(self) -> float:
        return round(self.memory_rss / 1048576, 2)

    @property
    def memory_total_mb(self) -> float:
        return round(self.memory_total / 1048576, 2)

    @property
    def gc_next_mb(self) -> float:
        return round(self.gc_next / 1048576, 2)


@dataclass(frozen=True)
class MockEsStats:
    """Parsed stats from mock-es's /_mock/stats endpoint."""

    docs_ingested: int
    batches: int
    bytes_received: int
    avg_batch_size: float
    docs_per_sec: float

    @property
    def bytes_received_mb(self) -> float:
        return round(self.bytes_received / 1048576, 2)


def _get(data: dict, *keys: str, default: int = 0) -> int | float:
    """Safely traverse nested dict keys."""
    current: dict | int | float = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def parse_filebeat_stats(data: dict) -> FilebeatStats:
    """Parse the JSON response from filebeat's /stats endpoint."""
    return FilebeatStats(
        events_total=int(_get(data, "libbeat", "pipeline", "events", "total")),
        events_acked=int(_get(data, "libbeat", "output", "events", "acked")),
        output_acked=int(_get(data, "libbeat", "output", "events", "acked")),
        output_failed=int(_get(data, "libbeat", "output", "events", "failed")),
        output_batches=int(_get(data, "libbeat", "output", "events", "batches")),
        memory_alloc=int(_get(data, "beat", "memstats", "memory_alloc")),
        memory_rss=int(_get(data, "beat", "memstats", "rss")),
        memory_total=int(_get(data, "beat", "memstats", "memory_total")),
        gc_next=int(_get(data, "beat", "memstats", "gc_next")),
        goroutines=int(_get(data, "beat", "runtime", "goroutines")),
        cpu_ticks=int(_get(data, "beat", "cpu", "total", "ticks")),
    )


def parse_mock_es_stats(data: dict) -> MockEsStats:
    """Parse the JSON response from mock-es's /_mock/stats endpoint."""
    return MockEsStats(
        docs_ingested=int(data.get("docs_ingested", 0)),
        batches=int(data.get("batches", 0)),
        bytes_received=int(data.get("bytes_received", 0)),
        avg_batch_size=float(data.get("avg_batch_size", 0)),
        docs_per_sec=float(data.get("docs_per_sec", 0)),
    )
