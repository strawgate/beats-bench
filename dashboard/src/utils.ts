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
