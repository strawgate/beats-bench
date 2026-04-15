#!/usr/bin/env bash
# local-run.sh — Build and benchmark a beats ref locally.
#
# Usage:
#   ./scripts/local-run.sh [ref] [scenario] [cpus] [runs]
#
# Examples:
#   ./scripts/local-run.sh main full-agent-dissect 1.0 3
#   ./scripts/local-run.sh my-feature-branch passthrough 0.5 2

set -euo pipefail

REF="${1:-main}"
SCENARIO="${2:-full-agent-dissect}"
CPUS="${3:-1.0}"
RUNS="${4:-3}"
MEASURE="${5:-20}"
BEATS_REPO="${BEATS_REPO:-https://github.com/elastic/beats.git}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BENCH_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "  Local Filebeat Benchmark"
echo "=========================================="
echo "  Ref:      $REF @ $BEATS_REPO"
echo "  Scenario: $SCENARIO"
echo "  CPUs: $CPUS, Runs: $RUNS, Measure: ${MEASURE}s"
echo ""

# Build binary
"$SCRIPT_DIR/build.sh" "$BEATS_REPO" "$REF" "$BENCH_ROOT/bin/bench"

# Prepare config
CONFIG="$BENCH_ROOT/pipelines/${SCENARIO}.yml"
if [ ! -f "$CONFIG" ]; then
  echo "ERROR: Pipeline config not found: $CONFIG"
  echo "Available: $(ls "$BENCH_ROOT/pipelines/"*.yml | xargs -I{} basename {} .yml | tr '\n' ' ')"
  exit 1
fi

# Copy config with root ownership for filebeat
TMPCONFIG=$(mktemp)
cp "$CONFIG" "$TMPCONFIG"

# Run benchmark via Python CLI
cd "$BENCH_ROOT"
uv run beats-bench run-benchmark \
  --binary "$BENCH_ROOT/bin/bench/filebeat" \
  --config "$TMPCONFIG" \
  --mock-es "$BENCH_ROOT/bin/mock-es" \
  --cpus "$CPUS" \
  --measure "$MEASURE" \
  --runs "$RUNS" \
  --scenario "$SCENARIO" \
  --output-dir "$BENCH_ROOT/results/${SCENARIO}-${CPUS}cpu"

rm -f "$TMPCONFIG"

echo ""
echo "Results: $BENCH_ROOT/results/${SCENARIO}-${CPUS}cpu/"
echo ""
echo "Benchmark-action output:"
cat "$BENCH_ROOT/results/${SCENARIO}-${CPUS}cpu/results.json"
