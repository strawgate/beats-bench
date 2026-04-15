# beats-bench

Filebeat pipeline benchmarking toolkit -- track processor throughput and resource usage over time using Docker-based benchmarks and [benchkit](https://github.com/strawgate/o11ykit) for data management and visualization.

## Dashboard

View benchmark trends and compare results at the live dashboard:
**[strawgate.github.io/beats-bench](https://strawgate.github.io/beats-bench/)**

## Quick Start

1. Go to [Actions -> Filebeat Pipeline Benchmark](../../actions/workflows/bench.yml)
2. Click **Run workflow**
3. Fill in the ref to benchmark
4. Results are stashed to the `bench-data` branch, aggregated into trend data, and shown on the dashboard

## Pipeline Scenarios

**Benchmark input (pure processor throughput, no I/O):**

| Scenario | Processors | What it measures |
|---|---|---|
| `full-agent-dissect` | rename + dissect + 6x add_fields + add_host_metadata | Full agent pipeline -- the realistic worst case |
| `full-agent-rename-only` | rename + 6x add_fields + add_host_metadata | Isolates rename clone skip from dissect |
| `enrichment-only` | 6x add_fields + add_host_metadata | Baseline enrichment cost (no clone-affected processors) |
| `passthrough` | (none) | Raw filebeat overhead -- output throughput ceiling |

**Real input types (includes I/O overhead):**

| Scenario | Input | Processors | What it measures |
|---|---|---|---|
| `filestream-dissect` | filestream (reads file) | rename + dissect + add_fields + add_host_metadata | File I/O + processor throughput |
| `tcp-syslog-dissect` | TCP :9000 | rename + dissect + add_fields + add_host_metadata | Network receive + processor throughput |
| `udp-syslog-dissect` | UDP :9000 | rename + dissect + add_fields + add_host_metadata | Network receive + processor throughput |
| `tcp-cef-rename` | TCP :9000 | rename + copy_fields + 6x add_fields + add_host_metadata | Security integration pattern (CEF over syslog) |

TCP/UDP/filestream scenarios require the `log-generator` tool to feed data into filebeat. Benchmark input scenarios are self-contained.

## How It Works

beats-bench uses [benchkit](https://github.com/strawgate/o11ykit) (from o11ykit) to handle the data pipeline:

1. **Benchmark** -- The Python runner executes filebeat with Docker, measures throughput and resource usage, and outputs results in [benchmark-action](https://github.com/benchmark-action/github-action-benchmark) JSON format.
2. **Stash** -- The `@benchkit` stash action commits results as OTLP metrics to the `bench-data` branch.
3. **Aggregate** -- The `@benchkit` aggregate action rebuilds the index and time-series files used by the dashboard.
4. **Visualize** -- The dashboard uses `@benchkit/chart` to render trend charts, regression detection, and run comparisons from the `bench-data` branch.

## Results

- **Dashboard**: [strawgate.github.io/beats-bench](https://strawgate.github.io/beats-bench/) -- trend charts, regression detection, run details
- **Artifacts**: CPU and allocation pprof profiles attached to each workflow run

## Local Development

See [DEVELOPING.md](DEVELOPING.md) for setup, build, and test instructions.

## Contributing

See [DEVELOPING.md](DEVELOPING.md) for repository structure, conventions, and how to add new scenarios.
