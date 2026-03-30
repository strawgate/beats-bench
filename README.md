# beats-bench

Filebeat pipeline benchmarking toolkit -- compare processor throughput between two commits using Docker-based benchmarks.

## Dashboard

View benchmark trends and compare results at the live dashboard:
**[strawgate.github.io/beats-bench](https://strawgate.github.io/beats-bench/)**

## Quick Start

1. Go to [Actions -> Filebeat Pipeline Benchmark](../../actions/workflows/bench.yml)
2. Click **Run workflow**
3. Fill in the base and PR refs to compare
4. Results appear in the job summary, artifacts, and dashboard

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

## Results

- **Dashboard**: [strawgate.github.io/beats-bench](https://strawgate.github.io/beats-bench/) -- trend charts and run comparison
- **Job summary**: Posted to each workflow run's Summary tab
- **Artifacts**: CPU and allocation pprof profiles attached to each workflow run

## Local Development

See [DEVELOPING.md](DEVELOPING.md) for setup, build, and test instructions.

## Contributing

See [DEVELOPING.md](DEVELOPING.md) for repository structure, conventions, and how to add new scenarios.
