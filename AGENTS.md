# Agent Instructions

## Repository Structure
- `src/beats_bench/` -- Python package (benchmark runner, data collection)
- `dashboard/` -- Preact app using @benchkit/chart (data visualization)
- `pipelines/` -- Filebeat pipeline configs (YAML)
- `mock-es/` -- Go mock Elasticsearch server
- `log-generator/` -- Go log line generator for TCP/UDP/file tests
- `.github/workflows/` -- GitHub Actions workflows

## Rules

### Python (`src/`, `tests/`)
- Ruff strict rules enforced (see pyproject.toml for full rule set)
- All functions must have type annotations
- Tests in `tests/` using pytest
- Run: `uv run pytest` and `uv run ruff check src/ tests/`
- Runner outputs benchmark-action JSON format consumed by benchkit actions

### Dashboard (`dashboard/`)
- Preact + @benchkit/chart, built with Vite
- Dashboard component handles routing, data fetching, and visualization
- Data fetched from raw.githubusercontent.com (bench-data branch) by @benchkit/chart
- Build: `cd dashboard && npm run build`

### Pipelines (`pipelines/`)
- Filebeat YAML configs, one per scenario
- Must include: benchmark input, processors, ES output, http/pprof enabled
- Output host must be `mock-es:9200`

### Workflows (`.github/workflows/`)
- bench.yml: benchmark workflow (build -> bench matrix -> stash/aggregate via benchkit)
- deploy-dashboard.yml: builds and deploys Preact app to GitHub Pages
- Uses strawgate/o11ykit/octo11y/actions for stash, aggregate, and compare

### Mock-ES (`mock-es/`)
- Go, no external dependencies
- Must handle: GET /, POST /_bulk, HEAD/GET/PUT for templates, GET /_mock/stats, POST /_mock/reset

### Log Generator (`log-generator/`)
- Go, no external dependencies
- Generates log lines for TCP, UDP, and file-based scenarios

## Key Decisions
- Data stored on `bench-data` branch in OTLP format, managed by benchkit actions
- Dashboard uses @benchkit/chart -- no custom data fetching or chart code
- Binaries cached by commit SHA in GitHub Actions cache
- No direct commits to gh-pages -- deploy via actions/deploy-pages
- Python requires 3.11+, ruff for linting, uv for project management
- Single-binary benchmarking model -- historical comparison via benchkit (not A/B alternating runs)
