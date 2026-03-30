#!/usr/bin/env bash
# run-one.sh — Run one benchmark iteration and output a JSON line with results.
#
# Usage: run-one.sh <binary-path> <config-path> <mock-es-path> <cpus> <measure-seconds> <label>
#
# The script starts mock-es and filebeat in Docker containers on bench-net,
# measures EPS over the given duration, collects resource & mock-es stats,
# then prints a single JSON line to stdout.

set -euo pipefail

BINARY_PATH="$1"
CONFIG_PATH="$2"
MOCK_ES_PATH="$3"
CPUS="$4"
MEASURE="$5"
LABEL="$6"

# ---------- helpers ----------
cleanup() {
  docker rm -f fb-bench mock-es-c >/dev/null 2>&1 || true
  sleep 1
}

die() { echo "ERROR: $*" >&2; cleanup; exit 1; }

json_field() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d${1})" 2>/dev/null
}

# ---------- cleanup any leftovers ----------
cleanup

# ---------- start mock-es ----------
docker run -d --name mock-es-c --network bench-net \
  -p 9200:9200 \
  -v "${MOCK_ES_PATH}:/mock-es:ro" --entrypoint /mock-es \
  debian:bookworm-slim >/dev/null 2>&1

# wait for mock-es to be ready
for i in $(seq 1 30); do
  curl -sf http://localhost:9200/ >/dev/null 2>&1 && break
  sleep 1
done
curl -sf http://localhost:9200/ >/dev/null 2>&1 || die "mock-es did not start"

# reset mock-es stats
curl -sf -XPOST http://localhost:9200/_mock/reset >/dev/null 2>&1 || true

# ---------- start filebeat ----------
docker run -d --name fb-bench --network bench-net \
  --cpus="${CPUS}" -p 5066:5066 \
  -v "$(cd "$(dirname "${BINARY_PATH}")" && pwd)/$(basename "${BINARY_PATH}"):/filebeat:ro" \
  -v "${CONFIG_PATH}:/filebeat.yml:ro" \
  --entrypoint /filebeat debian:bookworm-slim \
  -e -c /filebeat.yml \
  -E "output.elasticsearch.hosts=[\"mock-es-c:9200\"]" \
  -E http.host=0.0.0.0 >/dev/null 2>&1

# wait for pprof / stats endpoint
for i in $(seq 1 30); do
  curl -sf http://localhost:5066/stats >/dev/null 2>&1 && break
  sleep 1
done
curl -sf http://localhost:5066/stats >/dev/null 2>&1 || die "filebeat stats endpoint did not start"

# ---------- wait for steady state ----------
# Wait until events are actually being acked (output connected, queue filling).
# Then wait for GC to settle (~3 GC cycles at typical pace).
for i in $(seq 1 60); do
  ACKED=$(curl -s http://localhost:5066/stats | json_field "['libbeat']['output']['events']['acked']" || echo 0)
  [ "$ACKED" -gt 0 ] 2>/dev/null && break
  sleep 1
done
sleep 5  # Let GC pacer stabilize after initial burst

# Reset mock-es counters so profile-run stats start clean
curl -sf -XPOST http://localhost:9200/_mock/reset >/dev/null 2>&1 || true

# Capture baseline allocs profile (for delta computation later)
curl -s http://localhost:5066/debug/pprof/allocs -o /dev/null 2>/dev/null || true

# ---------- measure ----------
START_EVENTS=$(curl -s http://localhost:5066/stats | json_field "['libbeat']['pipeline']['events']['total']")
sleep "${MEASURE}"
END_EVENTS=$(curl -s http://localhost:5066/stats | json_field "['libbeat']['pipeline']['events']['total']")
EVENTS=$((END_EVENTS - START_EVENTS))
EPS=$((EVENTS / MEASURE))

# ---------- collect filebeat stats ----------
FB_STATS=$(curl -s http://localhost:5066/stats)
MEM_ALLOC=$(echo "$FB_STATS" | json_field "['beat']['memstats']['memory_alloc']" || echo 0)
MEM_RSS=$(echo "$FB_STATS" | json_field "['beat']['memstats']['rss']" || echo 0)
GC_NEXT=$(echo "$FB_STATS" | json_field "['beat']['memstats']['gc_next']" || echo 0)
GOROUTINES=$(echo "$FB_STATS" | json_field "['beat']['runtime']['goroutines']" || echo 0)

OUTPUT_ACKED=$(echo "$FB_STATS" | json_field "['libbeat']['output']['events']['acked']" || echo 0)
OUTPUT_FAILED=$(echo "$FB_STATS" | json_field "['libbeat']['output']['events']['failed']" || echo 0)
OUTPUT_BATCHES=$(echo "$FB_STATS" | json_field "['libbeat']['output']['events']['batches']" || echo 0)

# ---------- collect mock-es stats ----------
MOCK_STATS=$(curl -s http://localhost:9200/_mock/stats)
MOCK_DOCS=$(echo "$MOCK_STATS" | json_field "['docs_ingested']" || echo 0)
MOCK_BATCHES=$(echo "$MOCK_STATS" | json_field "['batches']" || echo 0)
MOCK_BYTES=$(echo "$MOCK_STATS" | json_field "['bytes_received']" || echo 0)
MOCK_AVG_BATCH=$(echo "$MOCK_STATS" | json_field "['avg_batch_size']" || echo 0)
MOCK_DPS=$(echo "$MOCK_STATS" | json_field "['docs_per_sec']" || echo 0)

# ---------- compute derived values ----------
MEM_ALLOC_MB=$(python3 -c "print(round(${MEM_ALLOC} / 1048576, 2))")
MEM_RSS_MB=$(python3 -c "print(round(${MEM_RSS} / 1048576, 2))")
GC_NEXT_MB=$(python3 -c "print(round(${GC_NEXT} / 1048576, 2))")
MOCK_BYTES_MB=$(python3 -c "print(round(${MOCK_BYTES} / 1048576, 2))")

# ---------- output JSON ----------
python3 -c "
import json, sys
print(json.dumps({
    'label': '${LABEL}',
    'eps': ${EPS},
    'events': ${EVENTS},
    'measure_sec': ${MEASURE},
    'memory_alloc_mb': ${MEM_ALLOC_MB},
    'memory_rss_mb': ${MEM_RSS_MB},
    'gc_next_mb': ${GC_NEXT_MB},
    'goroutines': ${GOROUTINES},
    'mock_docs': ${MOCK_DOCS},
    'mock_batches': ${MOCK_BATCHES},
    'mock_bytes_mb': ${MOCK_BYTES_MB},
    'mock_avg_batch': ${MOCK_AVG_BATCH},
    'mock_docs_per_sec': ${MOCK_DPS},
    'output_acked': ${OUTPUT_ACKED},
    'output_failed': ${OUTPUT_FAILED},
    'output_batches': ${OUTPUT_BATCHES},
}))
"

# ---------- cleanup ----------
cleanup
