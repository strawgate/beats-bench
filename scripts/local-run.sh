#!/usr/bin/env bash
# local-run.sh — Build and benchmark two beats refs locally.
#
# Usage:
#   ./scripts/local-run.sh [base-ref] [pr-ref] [scenario] [cpus] [runs]
#
# Examples:
#   ./scripts/local-run.sh main my-feature-branch full-agent-dissect 1.0 3
#   ./scripts/local-run.sh main main passthrough 0.5 2  # sanity check

set -euo pipefail

BASE_REF="${1:-main}"
PR_REF="${2:-main}"
SCENARIO="${3:-full-agent-dissect}"
CPUS="${4:-1.0}"
RUNS="${5:-3}"
MEASURE="${6:-20}"
BASE_REPO="${BASE_REPO:-https://github.com/elastic/beats.git}"
PR_REPO="${PR_REPO:-$BASE_REPO}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BENCH_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "  Local Filebeat Benchmark"
echo "=========================================="
echo "  Base: $BASE_REF @ $BASE_REPO"
echo "  PR:   $PR_REF @ $PR_REPO"
echo "  Scenario: $SCENARIO"
echo "  CPUs: $CPUS, Runs: $RUNS, Measure: ${MEASURE}s"
echo ""

# Build both binaries
"$SCRIPT_DIR/build.sh" "$BASE_REPO" "$BASE_REF" "$BENCH_ROOT/bin/base"
"$SCRIPT_DIR/build.sh" "$PR_REPO" "$PR_REF" "$BENCH_ROOT/bin/pr"

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

# Run benchmark
"$SCRIPT_DIR/run-scenario.sh" \
  "$BENCH_ROOT/bin/base/filebeat" \
  "$BENCH_ROOT/bin/pr/filebeat" \
  "$TMPCONFIG" \
  "$BENCH_ROOT/bin/mock-es" \
  "$CPUS" \
  "$MEASURE" \
  "$RUNS" \
  "$BENCH_ROOT/results/${SCENARIO}-${CPUS}cpu"

rm -f "$TMPCONFIG"

echo ""
echo "Results: $BENCH_ROOT/results/${SCENARIO}-${CPUS}cpu/"
cat "$BENCH_ROOT/results/${SCENARIO}-${CPUS}cpu/results.txt"
