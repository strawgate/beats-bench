#!/usr/bin/env bash
# build.sh — Build filebeat and mock-es inside Docker so binaries match the runtime.
#
# Usage:
#   ./scripts/build.sh <beats-repo-url> <ref> <output-dir>
#   ./scripts/build.sh https://github.com/elastic/beats.git main ./bin/base
#   ./scripts/build.sh https://github.com/strawgate/beats.git my-branch ./bin/pr
#
# Also builds mock-es from this repo if not already present.
#
# Outputs:
#   {output-dir}/filebeat     — linux/amd64 filebeat binary
#   ./bin/mock-es             — linux/amd64 mock-es binary (shared across builds)

set -euo pipefail

REPO_URL="${1:?Usage: $0 <beats-repo-url> <ref> <output-dir>}"
REF="${2:?Usage: $0 <beats-repo-url> <ref> <output-dir>}"
OUTPUT_DIR="${3:?Usage: $0 <beats-repo-url> <ref> <output-dir>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BENCH_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$OUTPUT_DIR"

echo "=== Building filebeat ==="
echo "  Repo: $REPO_URL"
echo "  Ref:  $REF"
echo ""

docker run --rm \
  -v "$OUTPUT_DIR:/output" \
  -e GOPROXY=https://proxy.golang.org,direct \
  golang:1.26 bash -c "
    set -euo pipefail
    git clone --depth 1 --branch '$REF' '$REPO_URL' /beats 2>&1 || \
      (git clone --depth 50 '$REPO_URL' /beats && cd /beats && git checkout '$REF')
    cd /beats/x-pack/filebeat
    CGO_ENABLED=0 GOFLAGS=-mod=mod go build -o /output/filebeat .
    echo \"Build ID: \$(go tool buildid /output/filebeat | cut -c1-16)\"
  "

echo "  Built: $(ls -lh "$OUTPUT_DIR/filebeat" | awk '{print $5}')"

# Build mock-es if not present
if [ ! -f "$BENCH_ROOT/bin/mock-es" ]; then
  echo ""
  echo "=== Building mock-es ==="
  mkdir -p "$BENCH_ROOT/bin"
  docker run --rm \
    -v "$BENCH_ROOT/mock-es:/src:ro" \
    -v "$BENCH_ROOT/bin:/output" \
    golang:1.26 bash -c "
      cd /src
      CGO_ENABLED=0 go build -o /output/mock-es .
    "
  echo "  Built: $(ls -lh "$BENCH_ROOT/bin/mock-es" | awk '{print $5}')"
fi

echo ""
echo "=== Done ==="
