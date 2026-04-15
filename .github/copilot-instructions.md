# Copilot Instructions

Read [AGENTS.md](../AGENTS.md) for repository structure, rules, and conventions.

## Additional Context
- This repo benchmarks Elastic Beats (filebeat) processor performance
- The Python package (`src/beats_bench/`) runs Docker-based benchmarks
- The Preact dashboard (`dashboard/`) uses @benchkit/chart to visualize results
- Data lives on the `bench-data` branch in OTLP format, managed by benchkit actions
- The benchmark runner outputs benchmark-action JSON, which benchkit parses into OTLP
