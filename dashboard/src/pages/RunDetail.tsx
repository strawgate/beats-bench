import { useState, useEffect } from 'preact/hooks';
import '../components/ChartSetup';
import { TimeSeriesChart } from '../components/TimeSeriesChart';
import { fetchRun } from '../api';
import { navigate } from '../router';
import { formatDate, deltaClass, formatDelta, formatNum, avg, scenarioName, scenarioSort } from '../utils';
import type { RunDetailData, ScenarioCpuMetrics, RunEntry, Sample } from '../types';

interface Props {
  runId: string;
}

interface FilteredScenario {
  scenario: string;
  cpu: string;
  metrics: ScenarioCpuMetrics;
}

export function RunDetail({ runId }: Props) {
  const [runData, setRunData] = useState<RunDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string | null>(null); // null = all
  const [expandedScenarios, setExpandedScenarios] = useState<Set<string>>(new Set());

  useEffect(() => {
    setRunData(null);
    setError(null);
    setActiveFilter(null);
    setExpandedScenarios(new Set());

    fetchRun(runId)
      .then((resp) => setRunData(resp.run_data || (resp as unknown as RunDetailData)))
      .catch((e: Error) => setError(e.message));
  }, [runId]);

  if (error) {
    return (
      <div class="container">
        <div class="error-state">Failed to load run data: {error}</div>
      </div>
    );
  }
  if (!runData) {
    return (
      <div class="container">
        <div class="loading-state">Loading run data...</div>
      </div>
    );
  }

  const allFiltered = getFilteredScenarios(runData, activeFilter);
  const scenarioKeys = getScenarioKeys(runData);

  function toggleExpand(key: string) {
    setExpandedScenarios((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  return (
    <div class="container">
      <div class="breadcrumb">
        <a
          href="#/"
          onClick={(e: MouseEvent) => {
            e.preventDefault();
            navigate('/');
          }}
        >
          Overview
        </a>
        <span class="breadcrumb-sep">/</span>
        <span>Run #{runId}</span>
      </div>

      <div class="site-header">
        <h1>
          {runData.base_ref} &rarr; {runData.pr_ref}
        </h1>
        <p>{formatDate(runData.date)}</p>
      </div>

      {/* Header stats */}
      <div class="run-header-grid">
        <div class="stat-box">
          <div class="stat-label">Base</div>
          <div class="stat-value"><code>{runData.base_ref}</code></div>
        </div>
        <div class="stat-box">
          <div class="stat-label">PR</div>
          <div class="stat-value"><code>{runData.pr_ref}</code></div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Date</div>
          <div class="stat-value">{formatDate(runData.date)}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Run ID</div>
          <div class="stat-value">
            <a
              href={`https://github.com/strawgate/beats-bench/actions/runs/${runData.id}`}
              target="_blank"
              rel="noopener"
            >
              #{runData.id}
            </a>
          </div>
        </div>
      </div>

      {/* Scenario tabs */}
      {scenarioKeys.length > 1 && (
        <div class="scenario-tabs">
          <button
            class={`scenario-tab ${activeFilter === null ? 'active' : ''}`}
            onClick={() => setActiveFilter(null)}
          >
            All
          </button>
          {scenarioKeys.map((key) => {
            // key is "scenario (cpu CPU)" — extract scenario for friendly name
            const scenarioId = key.replace(/ \(.*$/, '');
            return (
              <button
                key={key}
                class={`scenario-tab ${activeFilter === key ? 'active' : ''}`}
                onClick={() => setActiveFilter(key)}
              >
                {scenarioName(scenarioId)} ({key.match(/\(([^)]+)\)/)?.[1] || ''})
              </button>
            );
          })}
        </div>
      )}

      {/* Scenario summary cards */}
      {allFiltered.map((f) => {
        const key = `${f.scenario}/${f.cpu}`;
        const baseAvg = Math.round(avg(f.metrics.base_eps));
        const prAvg = Math.round(avg(f.metrics.pr_eps));
        const delta = baseAvg > 0 ? ((prAvg - baseAvg) / baseAvg) * 100 : 0;

        const lastBase = f.metrics.base_runs?.[f.metrics.base_runs.length - 1];
        const lastPr = f.metrics.pr_runs?.[f.metrics.pr_runs.length - 1];
        const allocDelta =
          lastBase && lastPr && lastBase.alloc_per_event > 0
            ? ((lastPr.alloc_per_event - lastBase.alloc_per_event) / lastBase.alloc_per_event) * 100
            : null;

        const isExpanded = expandedScenarios.has(key);

        return (
          <div key={key}>
            <div
              class="scenario-card"
              onClick={() => toggleExpand(key)}
            >
              <div class="scenario-card-header">
                <span class="scenario-card-title">
                  {scenarioName(f.scenario)} ({f.cpu} CPU)
                </span>
                <div class="scenario-card-stats">
                  <div class="scenario-stat">
                    <div class="scenario-stat-label">Base EPS</div>
                    <div class="scenario-stat-value" style={{ color: 'var(--base-color)' }}>
                      {baseAvg.toLocaleString()}
                    </div>
                  </div>
                  <div class="scenario-stat">
                    <div class="scenario-stat-label">PR EPS</div>
                    <div class={`scenario-stat-value ${delta > 2 ? 'pr-value-positive' : delta < -2 ? 'pr-value-negative' : 'pr-value-neutral'}`}>
                      {prAvg.toLocaleString()}
                    </div>
                  </div>
                  <div class="scenario-stat">
                    <div class="scenario-stat-label">Delta</div>
                    <div class={`scenario-stat-value ${deltaClass(delta)}`} style={{ fontSize: '18px', fontWeight: 700 }}>
                      {formatDelta(delta)}
                    </div>
                  </div>
                  {allocDelta !== null && (
                    <div class="scenario-stat">
                      <div class="scenario-stat-label">Alloc/event</div>
                      <div class={`scenario-stat-value ${deltaClass(-allocDelta)}`}>
                        {formatDelta(allocDelta)}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                {isExpanded ? 'Click to collapse' : 'Click to expand details'}
              </div>
            </div>

            {isExpanded && <ScenarioDetail filtered={f} />}
          </div>
        );
      })}

      {/* Profiles link */}
      <div class="card">
        <h2>Profiles</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          CPU and allocation profiles are available as workflow artifacts.{' '}
          <a
            href={`https://github.com/strawgate/beats-bench/actions/runs/${runData.id}`}
            target="_blank"
            rel="noopener"
          >
            View on GitHub Actions
          </a>
        </p>
      </div>
    </div>
  );
}

function ScenarioDetail({ filtered }: { filtered: FilteredScenario }) {
  const { metrics } = filtered;

  const lastBase = metrics.base_runs?.[metrics.base_runs.length - 1];
  const lastPr = metrics.pr_runs?.[metrics.pr_runs.length - 1];
  const baseSamples = lastBase?.samples || [];
  const prSamples = lastPr?.samples || [];

  const hasSamples = baseSamples.length > 0 || prSamples.length > 0;

  return (
    <div class="detail-section">
      {/* Time-series charts */}
      {hasSamples && (
        <div class="card">
          <h2>Time-Series (Measurement Window)</h2>
          <div class="chart-grid">
            <EPSOverTimeChart baseSamples={baseSamples} prSamples={prSamples} />
            <HeapChart baseSamples={baseSamples} prSamples={prSamples} />
            <RSSChart baseSamples={baseSamples} prSamples={prSamples} />
          </div>
        </div>
      )}

      {/* Resource table */}
      <div class="card">
        <h2>Resource Comparison</h2>
        <ResourceTable base={lastBase} pr={lastPr} />
      </div>

      {/* Mock-ES table */}
      <div class="card">
        <h2>Mock-ES Sink Stats</h2>
        <MockESTable base={lastBase} pr={lastPr} />
      </div>
    </div>
  );
}

function computeEPS(samples: Sample[]): { labels: string[]; data: number[] } {
  if (samples.length < 2) return { labels: [], data: [] };
  const labels: string[] = [];
  const data: number[] = [];
  for (let i = 1; i < samples.length; i++) {
    const dt = samples[i].elapsed_sec - samples[i - 1].elapsed_sec;
    const de = samples[i].events - samples[i - 1].events;
    labels.push(samples[i].elapsed_sec + 's');
    data.push(dt > 0 ? Math.round(de / dt) : 0);
  }
  return { labels, data };
}

function extractMetric(
  samples: Sample[],
  key: 'mem_bytes' | 'rss_bytes',
  scale: number,
): { labels: string[]; data: number[] } {
  return {
    labels: samples.map((s) => s.elapsed_sec + 's'),
    data: samples.map((s) => s[key] / scale),
  };
}

function mergeLabels(a: string[], b: string[]): string[] {
  return a.length >= b.length ? a : b;
}

function EPSOverTimeChart({
  baseSamples,
  prSamples,
}: {
  baseSamples: Sample[];
  prSamples: Sample[];
}) {
  const baseEPS = computeEPS(baseSamples);
  const prEPS = computeEPS(prSamples);
  return (
    <TimeSeriesChart
      title="EPS over time"
      labels={mergeLabels(baseEPS.labels, prEPS.labels)}
      baseData={baseEPS.data}
      prData={prEPS.data}
      yLabel="Events/sec"
    />
  );
}

function HeapChart({
  baseSamples,
  prSamples,
}: {
  baseSamples: Sample[];
  prSamples: Sample[];
}) {
  const MB = 1024 * 1024;
  const baseMem = extractMetric(baseSamples, 'mem_bytes', MB);
  const prMem = extractMetric(prSamples, 'mem_bytes', MB);
  return (
    <TimeSeriesChart
      title="Heap Alloc (MB)"
      labels={mergeLabels(baseMem.labels, prMem.labels)}
      baseData={baseMem.data}
      prData={prMem.data}
      yLabel="MB"
    />
  );
}

function RSSChart({
  baseSamples,
  prSamples,
}: {
  baseSamples: Sample[];
  prSamples: Sample[];
}) {
  const MB = 1024 * 1024;
  const baseRSS = extractMetric(baseSamples, 'rss_bytes', MB);
  const prRSS = extractMetric(prSamples, 'rss_bytes', MB);
  return (
    <TimeSeriesChart
      title="RSS (MB)"
      labels={mergeLabels(baseRSS.labels, prRSS.labels)}
      baseData={baseRSS.data}
      prData={prRSS.data}
      yLabel="MB"
    />
  );
}

function ResourceTable({ base, pr }: { base?: RunEntry; pr?: RunEntry }) {
  const rows: { label: string; variant: 'base' | 'pr'; run: RunEntry }[] = [];
  if (base) rows.push({ label: 'Base', variant: 'base', run: base });
  if (pr) rows.push({ label: 'PR', variant: 'pr', run: pr });

  if (rows.length === 0) {
    return <p style={{ color: 'var(--text-secondary)' }}>No resource data</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Variant</th>
          <th class="num">Alloc (MB)</th>
          <th class="num">RSS (MB)</th>
          <th class="num">Alloc/event</th>
          <th class="num">Bytes/event</th>
          <th class="num">GC Next (MB)</th>
          <th class="num">Goroutines</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ label, variant, run }) => (
          <tr key={variant}>
            <td>
              <span class={`variant-label variant-${variant}`}>{label}</span>
            </td>
            <td class="num">{formatNum(run.memory_alloc_mb, 1)}</td>
            <td class="num">{formatNum(run.memory_rss_mb, 1)}</td>
            <td class="num">{formatNum(run.alloc_per_event)}</td>
            <td class="num">{formatNum(run.bytes_per_event)}</td>
            <td class="num">{formatNum(run.gc_next_mb, 1)}</td>
            <td class="num">{formatNum(run.goroutines)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function MockESTable({ base, pr }: { base?: RunEntry; pr?: RunEntry }) {
  const rows: { label: string; variant: 'base' | 'pr'; run: RunEntry }[] = [];
  if (base) rows.push({ label: 'Base', variant: 'base', run: base });
  if (pr) rows.push({ label: 'PR', variant: 'pr', run: pr });

  if (rows.length === 0) {
    return <p style={{ color: 'var(--text-secondary)' }}>No mock-ES data</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Variant</th>
          <th class="num">Docs</th>
          <th class="num">Batches</th>
          <th class="num">Avg Batch</th>
          <th class="num">Bytes (MB)</th>
          <th class="num">Docs/sec</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ label, variant, run }) => (
          <tr key={variant}>
            <td>
              <span class={`variant-label variant-${variant}`}>{label}</span>
            </td>
            <td class="num">{formatNum(run.mock_docs)}</td>
            <td class="num">{formatNum(run.mock_batches)}</td>
            <td class="num">{formatNum(run.mock_avg_batch, 0)}</td>
            <td class="num">{formatNum(run.mock_bytes_mb, 0)}</td>
            <td class="num">{formatNum(run.mock_docs_per_sec, 0)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function getScenarioKeys(runData: RunDetailData): string[] {
  const keys: string[] = [];
  for (const [scenario, cpuData] of Object.entries(runData.scenarios || {})) {
    for (const cpu of Object.keys(cpuData)) {
      keys.push(`${scenario} (${cpu} CPU)`);
    }
  }
  return keys;
}

function getFilteredScenarios(
  runData: RunDetailData,
  activeFilter: string | null,
): FilteredScenario[] {
  const result: FilteredScenario[] = [];
  for (const [scenario, cpuData] of Object.entries(runData.scenarios || {})) {
    for (const [cpu, metrics] of Object.entries(cpuData)) {
      const key = `${scenario} (${cpu} CPU)`;
      if (activeFilter && key !== activeFilter) continue;
      result.push({ scenario, cpu, metrics });
    }
  }
  result.sort((a, b) => scenarioSort(a.scenario, b.scenario));
  return result;
}
