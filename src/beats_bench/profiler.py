"""Collect pprof profiles from a running filebeat (replaces collect-profiles.sh)."""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.error
import urllib.request

PPROF_BASE = "http://localhost:5066/debug/pprof"


def _download(url: str, output_path: str, *, timeout: int = 300) -> bool:
    """Download a URL to a file. Returns True on success."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
        with open(output_path, "wb") as f:
            f.write(data)
        return True
    except (urllib.error.URLError, OSError) as exc:
        print(f"WARNING: failed to download {url}: {exc}", file=sys.stderr)
        return False


def collect_profiles(output_dir: str, label: str, measure_seconds: int) -> None:
    """Collect CPU, allocs, and heap profiles from a running filebeat.

    Assumes filebeat is already running with pprof on localhost:5066.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Verify pprof endpoint is reachable
    try:
        urllib.request.urlopen(f"{PPROF_BASE}/", timeout=5)
    except (urllib.error.URLError, OSError):
        print("ERROR: pprof endpoint not reachable at localhost:5066", file=sys.stderr)
        return

    # Capture "before" allocs profile (baseline for delta computation)
    print(f"Capturing pre-measurement allocs snapshot (label={label})...", file=sys.stderr)
    _download(
        f"{PPROF_BASE}/allocs",
        os.path.join(output_dir, f"{label}-allocs-before.pprof"),
    )

    # Collect CPU profile (blocks for measure_seconds)
    print(
        f"Collecting CPU profile for {measure_seconds}s (label={label})...",
        file=sys.stderr,
    )
    cpu_proc = subprocess.Popen(
        [
            "curl",
            "-s",
            f"{PPROF_BASE}/profile?seconds={measure_seconds}",
            "-o",
            os.path.join(output_dir, f"{label}-cpu.pprof"),
        ],
    )

    # Wait for CPU profile to finish
    cpu_proc.wait(timeout=measure_seconds + 30)

    # Capture "after" profiles
    print("Collecting allocs profile...", file=sys.stderr)
    _download(
        f"{PPROF_BASE}/allocs",
        os.path.join(output_dir, f"{label}-allocs.pprof"),
    )

    print("Collecting heap profile...", file=sys.stderr)
    _download(
        f"{PPROF_BASE}/heap",
        os.path.join(output_dir, f"{label}-heap.pprof"),
    )

    print(
        f"Profiles saved to {output_dir}/{label}-{{cpu,allocs,allocs-before,heap}}.pprof",
        file=sys.stderr,
    )
