#!/usr/bin/env bash
# collect-profiles.sh — Collect pprof profiles from a running filebeat.
#
# Usage: collect-profiles.sh <output-dir> <label> <measure-seconds>
#
# Assumes filebeat is already running with pprof on localhost:5066.
# Collects CPU (for measure-seconds), allocs, and heap profiles.

set -euo pipefail

OUTPUT_DIR="$1"
LABEL="$2"
MEASURE="$3"

mkdir -p "${OUTPUT_DIR}"

# Verify the pprof endpoint is reachable
curl -sf http://localhost:5066/debug/pprof/ >/dev/null 2>&1 || {
  echo "ERROR: pprof endpoint not reachable at localhost:5066" >&2
  exit 1
}

# Capture "before" allocs profile (baseline for delta computation)
echo "Capturing pre-measurement allocs snapshot (label=${LABEL})..." >&2
curl -s "http://localhost:5066/debug/pprof/allocs" \
  -o "${OUTPUT_DIR}/${LABEL}-allocs-before.pprof" || true

echo "Collecting CPU profile for ${MEASURE}s (label=${LABEL})..." >&2
curl -s "http://localhost:5066/debug/pprof/profile?seconds=${MEASURE}" \
  -o "${OUTPUT_DIR}/${LABEL}-cpu.pprof" &
PROF_PID=$!

# Wait for the CPU profile to finish (duration + small buffer)
sleep $((MEASURE + 2))
wait "${PROF_PID}" 2>/dev/null || true

# Capture "after" profiles
echo "Collecting allocs profile..." >&2
curl -s "http://localhost:5066/debug/pprof/allocs" \
  -o "${OUTPUT_DIR}/${LABEL}-allocs.pprof" || true

echo "Collecting heap profile..." >&2
curl -s "http://localhost:5066/debug/pprof/heap" \
  -o "${OUTPUT_DIR}/${LABEL}-heap.pprof" || true

echo "Profiles saved to ${OUTPUT_DIR}/${LABEL}-{cpu,allocs,allocs-before,heap}.pprof" >&2
echo "  To view delta allocs: go tool pprof -diff_base ${OUTPUT_DIR}/${LABEL}-allocs-before.pprof ${OUTPUT_DIR}/${LABEL}-allocs.pprof" >&2
