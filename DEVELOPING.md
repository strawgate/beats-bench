# Developing beats-bench

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker | latest | Run filebeat + mock-es containers |
| Python | 3.11+ | Benchmark runner, summarization |
| uv | latest | Python project/dependency management |
| Node.js | 22+ | Dashboard development |
| Go | 1.23+ | Build mock-es and log-generator |

## Repository Structure

```
beats-bench/
  src/beats_bench/       Python package — benchmark runner, data collection, summarization
    cli.py                 CLI entry point (beats-bench command)
    runner.py              Runs filebeat in Docker, collects metrics
    scenario.py            Scenario config loading and validation
    docker.py              Docker container management
    stats.py               Statistical analysis of benchmark results
    profiler.py            pprof profile collection
    summarize.py           Markdown summary and data aggregation
  dashboard/             Preact + TypeScript app — benchmark visualization
  pipelines/             Filebeat YAML configs — one per benchmark scenario
  mock-es/               Go mock Elasticsearch server — accepts _bulk, returns stats
  log-generator/         Go log line generator — feeds TCP/UDP/file inputs
  scripts/               Shell scripts — build.sh, local-run.sh
  tests/                 pytest tests for the Python package
  data/                  Local data directory (run results)
  .github/workflows/    GitHub Actions — bench.yml, deploy-dashboard.yml
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
2. Add statistical processing in `stats.py`
3. Include it in the summary output in `summarize.py`
4. Add a test in `tests/`

## Dashboard

The dashboard is a Preact + TypeScript + Chart.js app built with Vite. It fetches data from the `bench-data` branch at runtime via `raw.githubusercontent.com`.

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

Output goes to `dashboard/dist/`.

### Adding a component

Components live in `dashboard/src/`. The app uses hash-based routing via `useState` -- there is no external router. Data types are defined inline.

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
3. Add the scenario name to the `scenarios` input default in `.github/workflows/bench.yml`
4. Test locally with `./scripts/local-run.sh main main your-scenario 1.0 3`

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

1. **build** -- Clones the beats repo at both refs, compiles filebeat in Docker, caches binaries by commit SHA
2. **bench** (matrix) -- Runs each scenario x CPU combination. Uses the Python runner to start mock-es + filebeat in Docker, collects metrics
3. **summarize** -- Aggregates results from all matrix jobs, generates markdown summary, pushes data to `bench-data` branch

### deploy-dashboard.yml

Triggered on pushes to `main` that change `dashboard/`. Builds the Preact app and deploys to GitHub Pages via `actions/deploy-pages`.

## Running Locally

### Using the convenience script

```bash
./scripts/local-run.sh <base-ref> <pr-ref> <scenario> <cpus> <runs>

# Example: compare a feature branch against main
./scripts/local-run.sh main my-feature-branch full-agent-dissect 1.0 3
```

The script builds both filebeat binaries, then runs the benchmark.

### Using the Python CLI directly

```bash
uv run beats-bench run-scenario \
  --base-binary ./bin/base/filebeat \
  --pr-binary ./bin/pr/filebeat \
  --config ./pipelines/full-agent-dissect.yml \
  --mock-es ./bin/mock-es \
  --cpus 1.0 \
  --measure 20 \
  --runs 3 \
  --output-dir ./results/full-agent-dissect-1.0cpu
```

## Data Model

Benchmark results are stored on the `bench-data` branch (not `main`). The dashboard fetches this data at runtime.

### Structure

```
bench-data branch:
  index.json            List of all runs with metadata (date, refs, scenarios)
  runs/
    {run-id}.json       Full results for one workflow run
```

Each run JSON contains:
- Workflow metadata (refs, repos, commit SHAs)
- Per-scenario results (events/sec, CPU usage, memory, pprof data)
- Statistical summaries (mean, stddev, min, max across repeated runs)

The summarize job pushes new data to this branch after each benchmark completes. The dashboard reads `index.json` to list available runs, then fetches individual run files on demand.
