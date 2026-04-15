# Developing beats-bench

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker | latest | Run filebeat + mock-es containers |
| Python | 3.11+ | Benchmark runner |
| uv | latest | Python project/dependency management |
| Node.js | 22+ | Dashboard development |
| Go | 1.23+ | Build mock-es and log-generator |

## Repository Structure

```
beats-bench/
  src/beats_bench/       Python package — benchmark runner, data collection
    cli.py                 CLI entry point (beats-bench command)
    runner.py              Runs filebeat in Docker, collects metrics
    benchmark.py           Orchestrates warmup + measurement runs, outputs benchmark-action JSON
    docker.py              Docker container management
    stats.py               Filebeat and mock-es stats parsing
    profiler.py            pprof profile collection
  dashboard/             Preact app using @benchkit/chart — benchmark visualization
  pipelines/             Filebeat YAML configs — one per benchmark scenario
  mock-es/               Go mock Elasticsearch server — accepts _bulk, returns stats
  log-generator/         Go log line generator — feeds TCP/UDP/file inputs
  scripts/               Shell scripts — build.sh, local-run.sh
  tests/                 pytest tests for the Python package
  .github/workflows/    GitHub Actions — bench.yml, deploy-dashboard.yml, ci.yml
  pyproject.toml         Python project config with ruff lint rules
```

## Python Package

### Install dependencies

```bash
uv sync
```

### Run tests

```bash
uv run pytest
```

### Lint and format

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

Ruff enforces strict rules (see `pyproject.toml` for the full rule set). All functions should have type annotations.

### Adding a new metric

1. Collect the metric in `runner.py` (from Docker stats, pprof, or mock-es `/stats`)
2. Add it to `RunResult.to_dict()` in `runner.py`
3. Add a benchmark-action entry in `benchmark.py` (`_to_benchmark_entries`)
4. Add a test in `tests/`

## Dashboard

The dashboard uses [`@benchkit/chart`](https://github.com/strawgate/o11ykit) to render benchmark trends, regressions, and run details. It fetches data from the `bench-data` branch at runtime via `raw.githubusercontent.com`.

### Run locally

```bash
cd dashboard
npm install
npm run dev
```

### Build for production

```bash
cd dashboard
npm run build
```

Output goes to `dashboard/dist/`. The `Dashboard` component from `@benchkit/chart` handles all data fetching and visualization -- the app itself is minimal.

## Pipelines

Each YAML file in `pipelines/` defines one benchmark scenario. A pipeline config is a standard filebeat configuration with specific requirements:

### Adding a new scenario

1. Create `pipelines/your-scenario.yml`
2. Include these required elements:
   - A `filebeat.inputs` section (benchmark, filestream, tcp, or udp type)
   - Any processors to benchmark
   - Elasticsearch output pointing to `mock-es:9200`
   - HTTP endpoint enabled (for health checks)
   - pprof enabled via `http.pprof.enabled: true`
3. Add metadata to `pipelines/scenarios.json`
4. Add the scenario name to the `scenarios` input default in `.github/workflows/bench.yml`
5. Test locally with `./scripts/local-run.sh main your-scenario 1.0 3`

## Mock-ES

A lightweight Go HTTP server that mimics Elasticsearch just enough for filebeat to send data. Located in `mock-es/`.

**What it handles:**
- `GET /` -- cluster info (version, name)
- `POST /_bulk` -- accepts bulk indexing requests, counts events
- `HEAD/GET/PUT` for index templates -- returns success
- `GET /_mock/stats` -- returns event count and byte count (benchmark measurement endpoint)
- `POST /_mock/reset` -- resets counters between runs

### Build

```bash
cd mock-es && go build -o mock-es .
```

The log-generator (`log-generator/`) works similarly -- it is a Go binary that sends log lines over TCP, UDP, or writes to a file for filestream scenarios.

```bash
cd log-generator && go build -o log-generator .
```

## Workflows

### bench.yml

The main benchmark workflow runs on schedule (daily) and on workflow dispatch.

**Jobs:**

1. **build** -- Clones the beats repo at the specified ref, compiles filebeat, caches binaries by commit SHA
2. **bench** (matrix) -- Runs each scenario x CPU combination. Uses the Python runner to start mock-es + filebeat in Docker, collects metrics, outputs benchmark-action JSON
3. **publish** -- Merges results from all matrix jobs, stashes to `bench-data` via benchkit, aggregates index and series data

### deploy-dashboard.yml

Triggered on pushes to `main` that change `dashboard/`. Builds the Preact app and deploys to GitHub Pages via `actions/deploy-pages`.

## Running Locally

### Using the convenience script

```bash
./scripts/local-run.sh <ref> <scenario> <cpus> <runs>

# Example: benchmark the main branch
./scripts/local-run.sh main full-agent-dissect 1.0 3
```

The script builds the filebeat binary, then runs the benchmark.

### Using the Python CLI directly

```bash
uv run beats-bench run-benchmark \
  --binary ./bin/bench/filebeat \
  --config ./pipelines/full-agent-dissect.yml \
  --mock-es ./bin/mock-es \
  --cpus 1.0 \
  --measure 20 \
  --runs 3 \
  --output-dir ./results/full-agent-dissect-1.0cpu
```

## Data Model

Benchmark results are stored on the `bench-data` branch (not `main`) in OTLP metrics format, managed by [benchkit](https://github.com/strawgate/o11ykit) actions.

### Structure

```
bench-data branch:
  data/
    index.json                          All runs with metadata
    index/
      refs.json                         Runs grouped by git ref
      prs.json                          Runs grouped by PR
      metrics.json                      Available metrics
    runs/
      {run-id}/benchmark.otlp.json      OTLP metrics for one workflow run
    series/
      {metric}.json                     Time-series data per metric
    views/
      runs/{run-id}/detail.json         Pre-computed run detail views
```

The benchkit `stash` action writes per-run OTLP files, `aggregate` builds the derived index/series/views, and `@benchkit/chart` reads them at runtime for the dashboard.
