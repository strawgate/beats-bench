export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function shortRef(ref: string | undefined, max = 24): string {
  if (!ref) return '';
  return ref.length > max ? ref.substring(0, max) + '...' : ref;
}

export function deltaClass(delta: number): string {
  if (delta > 2) return 'delta-positive';
  if (delta < -2) return 'delta-negative';
  return 'delta-neutral';
}

export function formatDelta(delta: number): string {
  const sign = delta >= 0 ? '+' : '';
  return `${sign}${delta.toFixed(1)}%`;
}

export function formatNum(val: number | null | undefined, decimals?: number): string {
  if (val == null) return 'N/A';
  if (decimals != null) return val.toFixed(decimals);
  return val.toLocaleString();
}

export function avg(arr: number[]): number {
  if (arr.length === 0) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

// Scenario metadata — friendly names and sort order
const SCENARIO_META: Record<string, { name: string; sort: number }> = {
  'passthrough': { name: 'Baseline (No Processors)', sort: 0 },
  'enrichment-only': { name: 'Enrichment Only', sort: 1 },
  'full-agent-rename-only': { name: 'Full Pipeline (Rename)', sort: 2 },
  'full-agent-dissect': { name: 'Full Pipeline (Dissect + Rename)', sort: 3 },
  'filestream-dissect': { name: 'File Input (Dissect)', sort: 4 },
  'tcp-syslog-dissect': { name: 'TCP Syslog (Dissect)', sort: 5 },
  'udp-syslog-dissect': { name: 'UDP Syslog (Dissect)', sort: 6 },
  'tcp-cef-rename': { name: 'TCP CEF (Security)', sort: 7 },
};

export function scenarioName(id: string): string {
  return SCENARIO_META[id]?.name ?? id;
}

export function scenarioSort(a: string, b: string): number {
  const sa = SCENARIO_META[a]?.sort ?? 99;
  const sb = SCENARIO_META[b]?.sort ?? 99;
  return sa - sb;
}
