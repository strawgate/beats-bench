"""Tests for parsing filebeat and mock-es stats."""

from __future__ import annotations

from beats_bench.stats import parse_filebeat_stats, parse_mock_es_stats


class TestParseFilebeatStats:
    def test_parse_full_response(self, filebeat_stats_json):
        stats = parse_filebeat_stats(filebeat_stats_json)

        assert stats.events_total == 155000
        assert stats.events_acked == 150000
        assert stats.output_acked == 150000
        assert stats.output_failed == 5
        assert stats.output_batches == 3000
        assert stats.memory_alloc == 18743296
        assert stats.memory_rss == 62914560
        assert stats.memory_total == 1572864000
        assert stats.gc_next == 25165824
        assert stats.goroutines == 42
        assert stats.cpu_ticks == 48230

    def test_derived_mb_values(self, filebeat_stats_json):
        stats = parse_filebeat_stats(filebeat_stats_json)

        assert stats.memory_alloc_mb == round(18743296 / 1048576, 2)
        assert stats.memory_rss_mb == round(62914560 / 1048576, 2)
        assert stats.memory_total_mb == round(1572864000 / 1048576, 2)
        assert stats.gc_next_mb == round(25165824 / 1048576, 2)

    def test_parse_empty_dict(self):
        stats = parse_filebeat_stats({})

        assert stats.events_total == 0
        assert stats.memory_alloc == 0
        assert stats.goroutines == 0
        assert stats.cpu_ticks == 0

    def test_parse_partial_data(self):
        data = {
            "libbeat": {
                "pipeline": {"events": {"total": 100}},
            },
        }
        stats = parse_filebeat_stats(data)

        assert stats.events_total == 100
        assert stats.memory_alloc == 0
        assert stats.output_acked == 0


class TestParseMockEsStats:
    def test_parse_full_response(self, mock_es_stats_json):
        stats = parse_mock_es_stats(mock_es_stats_json)

        assert stats.docs_ingested == 150000
        assert stats.batches == 3000
        assert stats.bytes_received == 75000000
        assert stats.avg_batch_size == 50.0
        assert stats.docs_per_sec == 7500.0

    def test_derived_mb(self, mock_es_stats_json):
        stats = parse_mock_es_stats(mock_es_stats_json)

        assert stats.bytes_received_mb == round(75000000 / 1048576, 2)

    def test_parse_empty_dict(self):
        stats = parse_mock_es_stats({})

        assert stats.docs_ingested == 0
        assert stats.batches == 0
        assert stats.bytes_received == 0
        assert stats.avg_batch_size == 0.0
        assert stats.docs_per_sec == 0.0
