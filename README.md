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
| `scenarios` | `with-dissect,worst-case` | Pipeline scenarios to test |
| `cpus` | `0.5,1.0` | Docker CPU limits |
| `runs_per_scenario` | `3` | Measurement runs per binary per scenario |
| `measurement_seconds` | `20` | Seconds to measure each run |

### Example: Compare a PR against main

```
base_ref: main
pr_ref: perf/skip-unnecessary-clone
beats_repo: elastic/beats
pr_repo: strawgate/beats
scenarios: with-dissect,worst-case
cpus: 0.5,1.0
```

### Pipeline scenarios

| Scenario | Description |
|---|---|
| `worst-case` | Full agent pipeline: dissect + rename + 6× add_fields + host/cloud/k8s/docker metadata |
| `with-dissect` | Dissect + rename + 6× add_fields + host + cloud/container/k8s metadata |
| `mid-case` | 4× add_fields + host metadata |
| `best-case` | 2× add_fields only |

## Results

- **Job summary**: Posted to the workflow run's Summary tab
- **Dashboard**: [Benchmark trends](https://strawgate.github.io/beats-bench/dev/bench/) (via github-action-benchmark)
- **Profiles**: CPU and allocation pprof files attached as workflow artifacts

## Architecture

1. **Build job**: Compiles filebeat from both refs in parallel
2. **Bench matrix**: Runs all scenario × CPU combinations in parallel
3. **Summarize**: Aggregates results into markdown table and benchmark dashboard
