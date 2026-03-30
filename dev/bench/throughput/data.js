window.BENCHMARK_DATA = {
  "lastUpdate": 1774893774553,
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
      },
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
          "id": "e7ca9ac9e31cadad9c4ca2e1a6a2d482abbd0748",
          "message": "Generate dashboard data JSON and push to gh-pages\n\nsummarize.py: new generate_dashboard_data() produces structured JSON\nwith per-scenario EPS, full run details with samples, and an index\nentry for the manifest.\n\nworkflow: new 'Publish custom dashboard data' step clones gh-pages,\nwrites data/runs/{id}.json and updates data/index.json, pushes.",
          "timestamp": "2026-03-30T17:51:55Z",
          "url": "https://github.com/strawgate/beats-bench/commit/e7ca9ac9e31cadad9c4ca2e1a6a2d482abbd0748"
        },
        "date": 1774893773699,
        "tool": "customBiggerIsBetter",
        "benches": [
          {
            "name": "full-agent-dissect (1.0 CPU) EPS",
            "value": 18258,
            "unit": "events/sec",
            "extra": "base=16194 delta=+12%"
          },
          {
            "name": "full-agent-dissect (1.0 CPU) mock docs/sec",
            "value": 18264,
            "unit": "docs/sec"
          },
          {
            "name": "full-agent-rename-only (1.0 CPU) EPS",
            "value": 20858,
            "unit": "events/sec",
            "extra": "base=18735 delta=+11%"
          },
          {
            "name": "full-agent-rename-only (1.0 CPU) mock docs/sec",
            "value": 20976,
            "unit": "docs/sec"
          },
          {
            "name": "passthrough (1.0 CPU) EPS",
            "value": 70347,
            "unit": "events/sec",
            "extra": "base=72765 delta=-4%"
          },
          {
            "name": "passthrough (1.0 CPU) mock docs/sec",
            "value": 71672,
            "unit": "docs/sec"
          }
        ]
      }
    ]
  }
}