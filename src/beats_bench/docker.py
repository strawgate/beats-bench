"""Docker container lifecycle helpers using subprocess."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request


def _run(
    args: list[str],
    *,
    check: bool = True,
    quiet: bool = True,
) -> subprocess.CompletedProcess:
    """Run a docker command."""
    return subprocess.run(
        args,
        check=check,
        capture_output=quiet,
        text=True,
    )


def ensure_network(name: str = "bench-net") -> None:
    """Create the Docker network if it doesn't exist."""
    _run(["docker", "network", "create", name], check=False)


def stop_all() -> None:
    """Remove benchmark containers."""
    _run(["docker", "rm", "-f", "fb-bench", "mock-es-c"], check=False)
    time.sleep(1)


def start_mock_es(mock_es_path: str, network: str = "bench-net") -> None:
    """Start the mock-es container."""
    _run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            "mock-es-c",
            "--network",
            network,
            "-p",
            "9200:9200",
            "-v",
            f"{mock_es_path}:/mock-es:ro",
            "--entrypoint",
            "/mock-es",
            "debian:bookworm-slim",
        ]
    )


def start_filebeat(
    binary_path: str,
    config_path: str,
    cpus: str,
    network: str = "bench-net",
) -> None:
    """Start the filebeat container."""
    _run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            "fb-bench",
            "--network",
            network,
            f"--cpus={cpus}",
            "-p",
            "5066:5066",
            "-v",
            f"{binary_path}:/filebeat:ro",
            "-v",
            f"{config_path}:/filebeat.yml:ro",
            "--entrypoint",
            "/filebeat",
            "debian:bookworm-slim",
            "-e",
            "-c",
            "/filebeat.yml",
            "-E",
            'output.elasticsearch.hosts=["mock-es-c:9200"]',
            "-E",
            "http.host=0.0.0.0",
        ]
    )


def wait_for_endpoint(url: str, timeout: int = 30) -> bool:
    """Poll a URL until it responds 200, or timeout."""
    for _ in range(timeout):
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    return False


def reset_mock_es() -> None:
    """Reset mock-es stats counters."""
    req = urllib.request.Request("http://localhost:9200/_mock/reset", method="POST")
    try:
        urllib.request.urlopen(req, timeout=5)
    except (urllib.error.URLError, OSError):
        pass


def fetch_json(url: str) -> dict:
    """Fetch JSON from a URL and return parsed dict."""
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        print(f"WARNING: failed to fetch {url}: {exc}", file=sys.stderr)
        return {}
