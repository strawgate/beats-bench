window.BENCHMARK_DATA = {
  "lastUpdate": 1774890979777,
  "repoUrl": "https://github.com/strawgate/beats-bench",
  "entries": {
    "Efficiency (lower is better)": [
      {
        "commit": {
          "author": {
            "name": "strawgate",
            "username": "strawgate",
            "email": "williamseaston@gmail.com"
          },
          "committer": {
            "name": "strawgate",
            "username": "strawgate",
            "email": "williamseaston@gmail.com"
          },
          "id": "6ee6240ac1c0b474767ffe27db06e951b9690415",
          "message": "Fix dashboard publishing and scenario naming\n\n- Add github-token to benchmark-action steps (required for auto-push to gh-pages)\n- Add --scenario argument to run-scenario CLI so pipeline names appear\n  correctly in results instead of 'fb-config'\n- Plumb scenario_name through scenario.py to results.txt",
          "timestamp": "2026-03-30T17:02:49Z",
          "url": "https://github.com/strawgate/beats-bench/commit/6ee6240ac1c0b474767ffe27db06e951b9690415"
        },
        "date": 1774890979131,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "full-agent-dissect (1.0 CPU) alloc/event",
            "value": 19893,
            "unit": "bytes",
            "extra": "base=26391"
          },
          {
            "name": "full-agent-dissect (1.0 CPU) bytes/event",
            "value": 1944,
            "unit": "bytes",
            "extra": "base=1948"
          },
          {
            "name": "full-agent-dissect (1.0 CPU) heap MB",
            "value": 19.2,
            "unit": "MB"
          },
          {
            "name": "passthrough (1.0 CPU) alloc/event",
            "value": 3479,
            "unit": "bytes",
            "extra": "base=3477"
          },
          {
            "name": "passthrough (1.0 CPU) bytes/event",
            "value": 567,
            "unit": "bytes",
            "extra": "base=567"
          },
          {
            "name": "passthrough (1.0 CPU) heap MB",
            "value": 11.6,
            "unit": "MB"
          }
        ]
      }
    ]
  }
}