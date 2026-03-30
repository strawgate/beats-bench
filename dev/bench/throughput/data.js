window.BENCHMARK_DATA = {
  "lastUpdate": 1774890977791,
  "repoUrl": "https://github.com/strawgate/beats-bench",
  "entries": {
    "Throughput (higher is better)": [
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
        "date": 1774890976923,
        "tool": "customBiggerIsBetter",
        "benches": [
          {
            "name": "full-agent-dissect (1.0 CPU) EPS",
            "value": 16658,
            "unit": "events/sec",
            "extra": "base=15130 delta=+10%"
          },
          {
            "name": "full-agent-dissect (1.0 CPU) mock docs/sec",
            "value": 16918,
            "unit": "docs/sec"
          },
          {
            "name": "passthrough (1.0 CPU) EPS",
            "value": 72260,
            "unit": "events/sec",
            "extra": "base=73690 delta=-2%"
          },
          {
            "name": "passthrough (1.0 CPU) mock docs/sec",
            "value": 72437,
            "unit": "docs/sec"
          }
        ]
      }
    ]
  }
}