import { useState, useEffect } from 'preact/hooks';
import '../components/ChartSetup';
import { SparklineChart } from '../components/SparklineChart';
import { fetchIndex } from '../api';
import { navigate } from '../router';
import { formatDate, shortRef, deltaClass, formatDelta, scenarioName } from '../utils';
import type { IndexData, IndexRun, SummaryEntry } from '../types';

export function Overview() {
  const [data, setData] = useState<IndexData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIndex().then(setData).catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <div class="container"><div class="error-state">{error}</div></div>;
  if (!data) return <div class="container"><div class="loading-state">Loading dashboard data...</div></div>;

  const runs = data.runs || [];
  if (runs.length === 0) {
    return (
      <div class="container">
        <Header />
        <div class="loading-state">No benchmark runs yet. Trigger a benchmark from GitHub Actions.</div>
      </div>
    );
  }

  const nightlyRuns = runs.filter((r) => r.type === 'nightly');
  const prRuns = runs.filter((r) => (r.type || 'pr') === 'pr' && r.pr_number);

  // Group PR runs by pr_number
  const prGroups = new Map<number, IndexRun[]>();
  for (const run of prRuns) {
    if (!run.pr_number) continue;
    const list = prGroups.get(run.pr_number) || [];
    list.push(run);
    prGroups.set(run.pr_number, list);
  }

  return (
    <div class="container">
      <Header />
      {nightlyRuns.length > 0 && <NightlySection runs={nightlyRuns} />}
      {prGroups.size > 0 && <PRSection groups={prGroups} />}
      <AllRunsSection runs={runs} />
    </div>
  );
}

function Header() {
  return (
    <div class="site-header">
      <h1>beats-bench</h1>
      <p>Filebeat pipeline benchmark results -- comparing PR performance against base branch</p>
      <div class="header-links">
        <a href="https://github.com/strawgate/beats-bench" target="_blank" rel="noopener">Repository</a>
        <a href="https://github.com/strawgate/beats-bench/actions/workflows/bench.yml" target="_blank" rel="noopener">Run Benchmark</a>
      </div>
    </div>
  );
}

function NightlySection({ runs }: { runs: IndexRun[] }) {
  // Group by scenario+cpu, collect EPS trend
  const combos = new Map<string, { date: string; value: number }[]>();
  for (const run of runs) {
    const summary = run.summary || {};
    for (const [scenario, cpuData] of Object.entries(summary)) {
      for (const [cpu, stats] of Object.entries(cpuData)) {
        const key = `${scenario} (${cpu} CPU)`;
        const list = combos.get(key) || [];
        list.push({ date: run.date, value: (stats as SummaryEntry).pr_avg || (stats as SummaryEntry).base_avg || 0 });
        combos.set(key, list);
      }
    }
  }

  return (
    <div class="card">
      <h2>Nightly Benchmarks</h2>
      <div class="nightly-grid">
        {Array.from(combos.entries()).map(([label, points]) => {
          const sorted = [...points].sort((a, b) => a.date.localeCompare(b.date));
          const latest = sorted[sorted.length - 1];
          return (
            <div class="nightly-card" key={label}>
              <div class="nightly-card-label">{label}</div>
              <div class="nightly-card-value">{latest.value.toLocaleString()} EPS</div>
              <SparklineChart data={sorted.map((p) => p.value)} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PRSection({ groups }: { groups: Map<number, IndexRun[]> }) {
  return (
    <div class="card">
      <h2>PR Benchmarks</h2>
      {Array.from(groups.entries()).map(([prNumber, runs]) => {
        const latest = runs[0]; // runs are chronological, newest first
        const prRepo = latest.pr_repo || 'elastic/beats';

        // Collect summary deltas from latest run
        const deltas: { key: string; entry: SummaryEntry }[] = [];
        const summary = latest.summary || {};
        for (const [scenario, cpuData] of Object.entries(summary)) {
          for (const [cpu, stats] of Object.entries(cpuData)) {
            deltas.push({ key: `${scenarioName(scenario)}/${cpu}`, entry: stats as SummaryEntry });
          }
        }

        return (
          <div class="pr-group" key={prNumber}>
            <div class="pr-group-header">
              <span class="pr-group-title">
                <a
                  href={`https://github.com/${prRepo}/pull/${prNumber}`}
                  target="_blank"
                  rel="noopener"
                >
                  #{prNumber}
                </a>
              </span>
              <span class="pr-group-refs">
                {shortRef(latest.base_ref)} &rarr; {shortRef(latest.pr_ref)}
                {' -- '}
                {runs.length} run{runs.length > 1 ? 's' : ''}
                {' -- '}
                <a
                  href={`#/run/${latest.id}`}
                  onClick={(e: MouseEvent) => {
                    e.preventDefault();
                    navigate(`/run/${latest.id}`);
                  }}
                >
                  Latest run
                </a>
              </span>
            </div>
            {deltas.length > 0 && (
              <div class="pr-group-summary">
                {deltas.map(({ key, entry }) => (
                  <span class="pr-summary-item" key={key}>
                    {key}:{' '}
                    <span class={`delta ${deltaClass(entry.delta_pct)}`}>
                      {formatDelta(entry.delta_pct)}
                    </span>
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function AllRunsSection({ runs }: { runs: IndexRun[] }) {
  return (
    <div class="card">
      <h2>All Runs</h2>
      {runs.map((run) => {
        const isNightly = run.type === 'nightly';
        // Collect deltas
        const deltas: { key: string; delta: number }[] = [];
        const summary = run.summary || {};
        for (const [scenario, cpuData] of Object.entries(summary)) {
          for (const [cpu, stats] of Object.entries(cpuData)) {
            deltas.push({ key: `${scenarioName(scenario)}/${cpu}`, delta: (stats as SummaryEntry).delta_pct });
          }
        }

        return (
          <a
            class="run-item"
            key={run.id}
            href={`#/run/${run.id}`}
            onClick={(e: MouseEvent) => {
              e.preventDefault();
              navigate(`/run/${run.id}`);
            }}
          >
            <div class="run-meta">
              <div class="run-refs">
                {shortRef(run.base_ref)} &rarr; {shortRef(run.pr_ref)}
                {run.pr_number ? ` -- PR #${run.pr_number}` : ''}
              </div>
              <div class="run-date">
                {formatDate(run.date)} -- Run #{run.id}
              </div>
              {deltas.length > 0 && (
                <div style={{ marginTop: '4px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  {deltas.map(({ key, delta }) => (
                    <span class="pr-summary-item" key={key}>
                      {key}:{' '}
                      <span class={`delta ${deltaClass(delta)}`}>
                        {formatDelta(delta)}
                      </span>
                    </span>
                  ))}
                </div>
              )}
            </div>
            {isNightly && (
              <div class="run-tags">
                <span class="tag tag-nightly">nightly</span>
              </div>
            )}
          </a>
        );
      })}
    </div>
  );
}
