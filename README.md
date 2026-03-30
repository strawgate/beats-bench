# beats-bench

Filebeat pipeline benchmarking with GitHub Actions.

## Usage

Go to [Actions → Filebeat Pipeline Benchmark](../../actions/workflows/bench.yml) and click **Run workflow**.

### Inputs

| Input | Default | Description |
|---|---|---|
| `base_ref` | `main` | Base branch/commit to benchmark against |
| `pr_ref` | `main` | PR branch/commit to benchmark |
| `beats_repo` | `elastic/beats` | Base beats repository |
| `pr_repo` | (same as beats_repo) | PR repository if different (e.g. `strawgate/beats`) |
| `scenarios` | `full-agent-dissect,full-agent-rename-only,enrichment-only,passthrough` | Pipeline scenarios to test |
| `cpus` | `0.5,1.0` | Docker CPU limits |
| `runs_per_scenario` | `3` | Measurement runs per binary per scenario |
| `measurement_seconds` | `20` | Seconds to measure each run |

### Example: Compare a PR against main

```
base_ref: main
pr_ref: claude-optimize-add-field-processors-ep8Ok
beats_repo: elastic/beats
pr_repo: strawgate/beats
scenarios: full-agent-dissect,full-agent-rename-only
cpus: 0.5,1.0
```

### Pipeline scenarios

**Benchmark input (pure processor throughput, no I/O):**

| Scenario | Processors | What it measures |
|---|---|---|
| `full-agent-dissect` | rename + dissect + 6× add_fields + add_host_metadata | Full agent pipeline — the realistic worst case |
| `full-agent-rename-only` | rename + 6× add_fields + add_host_metadata | Isolates rename clone skip from dissect |
| `enrichment-only` | 6× add_fields + add_host_metadata | Baseline enrichment cost (no clone-affected processors) |
| `passthrough` | (none) | Raw filebeat overhead — output throughput ceiling |

**Real input types (includes I/O overhead):**

| Scenario | Input | Processors | What it measures |
|---|---|---|---|
| `filestream-dissect` | filestream (reads file) | rename + dissect + add_fields + add_host_metadata | File I/O + processor throughput |
| `tcp-syslog-dissect` | TCP :9000 | rename + dissect + add_fields + add_host_metadata | Network receive + processor throughput |
| `udp-syslog-dissect` | UDP :9000 | rename + dissect + add_fields + add_host_metadata | Network receive + processor throughput |
| `tcp-cef-rename` | TCP :9000 | rename + copy_fields + 6× add_fields + add_host_metadata | Security integration pattern (CEF over syslog) |

The TCP/UDP/filestream scenarios require the `log-generator` tool to feed data into filebeat. The benchmark input scenarios are self-contained.

## Results

- **Job summary**: Posted to the workflow run's Summary tab
- **Dashboard**: [Benchmark trends](https://strawgate.github.io/beats-bench/dev/bench/) (via github-action-benchmark)
- **Profiles**: CPU and allocation pprof files attached as workflow artifacts

## Architecture

1. **Build job**: Compiles filebeat from both refs in parallel
2. **Bench matrix**: Runs all scenario × CPU combinations in parallel
3. **Summarize**: Aggregates results into markdown table and benchmark dashboard
