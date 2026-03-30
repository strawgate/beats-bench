#!/usr/bin/env bash
# run-scenario.sh — Run a full benchmark scenario (warmup + N alternating runs + profiles).
#
# Usage: run-scenario.sh <base-binary> <pr-binary> <config-path> <mock-es-path> \
#                         <cpus> <measure-seconds> <runs> <output-dir>
#
# Outputs:
#   {output-dir}/runs.jsonl   — one JSON line per measurement run
#   {output-dir}/results.txt  — summary in key=value format
#   {output-dir}/*.pprof      — CPU, allocs, heap profiles for each variant

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

BASE_BINARY="$1"
PR_BINARY="$2"
CONFIG_PATH="$3"
MOCK_ES_PATH="$4"
CPUS="$5"
MEASURE="$6"
RUNS="$7"
OUTPUT_DIR="$8"

mkdir -p "${OUTPUT_DIR}"

# ---------- ensure docker network exists ----------
docker network create bench-net 2>/dev/null || true

# ---------- warmup (discarded) ----------
echo "=== Warmup run (discarded) ==="
"${SCRIPT_DIR}/run-one.sh" "${BASE_BINARY}" "${CONFIG_PATH}" "${MOCK_ES_PATH}" \
  "${CPUS}" "${MEASURE}" "warmup" >/dev/null

# ---------- alternating measurement runs ----------
BASE_EPS_LIST=""
PR_EPS_LIST=""
JSONL_FILE="${OUTPUT_DIR}/runs.jsonl"
> "${JSONL_FILE}"

for i in $(seq 1 "${RUNS}"); do
  if [ $((i % 2)) -eq 1 ]; then
    FIRST_LABEL="base"  FIRST_BIN="${BASE_BINARY}"
    SECOND_LABEL="pr"   SECOND_BIN="${PR_BINARY}"
  else
    FIRST_LABEL="pr"    FIRST_BIN="${PR_BINARY}"
    SECOND_LABEL="base" SECOND_BIN="${BASE_BINARY}"
  fi

  echo "=== Run ${i}/${RUNS}: ${FIRST_LABEL} first ==="

  FIRST_JSON=$("${SCRIPT_DIR}/run-one.sh" "${FIRST_BIN}" "${CONFIG_PATH}" "${MOCK_ES_PATH}" \
    "${CPUS}" "${MEASURE}" "${FIRST_LABEL}")
  echo "${FIRST_JSON}" >> "${JSONL_FILE}"

  SECOND_JSON=$("${SCRIPT_DIR}/run-one.sh" "${SECOND_BIN}" "${CONFIG_PATH}" "${MOCK_ES_PATH}" \
    "${CPUS}" "${MEASURE}" "${SECOND_LABEL}")
  echo "${SECOND_JSON}" >> "${JSONL_FILE}"

  FIRST_EPS=$(echo "${FIRST_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin)['eps'])")
  SECOND_EPS=$(echo "${SECOND_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin)['eps'])")

  if [ "${FIRST_LABEL}" = "base" ]; then
    B_EPS="${FIRST_EPS}"; P_EPS="${SECOND_EPS}"
  else
    B_EPS="${SECOND_EPS}"; P_EPS="${FIRST_EPS}"
  fi

  BASE_EPS_LIST="${BASE_EPS_LIST}${B_EPS},"
  PR_EPS_LIST="${PR_EPS_LIST}${P_EPS},"
  echo "  Run ${i}: base=${B_EPS} pr=${P_EPS}"
done

# ---------- profile collection ----------
for LABEL in base pr; do
  if [ "${LABEL}" = "base" ]; then BIN="${BASE_BINARY}"; else BIN="${PR_BINARY}"; fi

  echo "=== Collecting profiles for ${LABEL} ==="

  # Start containers for profile collection (reuse run-one.sh's container setup logic)
  docker rm -f fb-bench mock-es-c >/dev/null 2>&1 || true
  sleep 1

  docker run -d --name mock-es-c --network bench-net \
    -p 9200:9200 \
    -v "${MOCK_ES_PATH}:/mock-es:ro" --entrypoint /mock-es \
    debian:bookworm-slim >/dev/null 2>&1

  for j in $(seq 1 30); do
    curl -sf http://localhost:9200/ >/dev/null 2>&1 && break
    sleep 1
  done

  docker run -d --name fb-bench --network bench-net \
    --cpus="${CPUS}" -p 5066:5066 \
    -v "$(cd "$(dirname "${BIN}")" && pwd)/$(basename "${BIN}"):/filebeat:ro" \
    -v "${CONFIG_PATH}:/filebeat.yml:ro" \
    --entrypoint /filebeat debian:bookworm-slim \
    -e -c /filebeat.yml \
    -E "output.elasticsearch.hosts=[\"mock-es-c:9200\"]" \
    -E http.host=0.0.0.0 >/dev/null 2>&1

  for j in $(seq 1 30); do
    curl -sf http://localhost:5066/stats >/dev/null 2>&1 && break
    sleep 1
  done
  sleep 5

  "${SCRIPT_DIR}/collect-profiles.sh" "${OUTPUT_DIR}" "${LABEL}" "${MEASURE}"

  docker rm -f fb-bench mock-es-c >/dev/null 2>&1 || true
  sleep 1
done

# ---------- write results.txt ----------
RESULTS_FILE="${OUTPUT_DIR}/results.txt"
{
  echo "scenario=$(basename "${CONFIG_PATH}" .yml)"
  echo "cpu=${CPUS}"
  echo "base_eps=${BASE_EPS_LIST%,}"
  echo "pr_eps=${PR_EPS_LIST%,}"
} > "${RESULTS_FILE}"

echo "=== Results ==="
cat "${RESULTS_FILE}"
echo "=== Benchmark complete. Output in ${OUTPUT_DIR}/ ==="
