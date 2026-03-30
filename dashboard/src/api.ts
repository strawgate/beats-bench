import type { IndexData, RunResponse } from './types';

// Data lives on the bench-data branch, served via raw.githubusercontent.com
const DATA_BASE = import.meta.env.DEV
  ? '/data/'  // Vite dev proxy
  : 'https://raw.githubusercontent.com/strawgate/beats-bench/bench-data/data/';

function dataUrl(path: string): string {
  return `${DATA_BASE}${path}`;
}

export async function fetchIndex(): Promise<IndexData> {
  const resp = await fetch(dataUrl('index.json'));
  if (!resp.ok) throw new Error(`Failed to load index: ${resp.status}`);
  return resp.json() as Promise<IndexData>;
}

export async function fetchRun(id: string): Promise<RunResponse> {
  const resp = await fetch(dataUrl(`runs/${id}.json`));
  if (!resp.ok) throw new Error(`Failed to load run ${id}: ${resp.status}`);
  return resp.json() as Promise<RunResponse>;
}
