export interface Sample {
  elapsed_sec: number;
  events: number;
  mem_bytes: number;
  rss_bytes: number;
}

export interface RunEntry {
  label: string;
  eps: number;
  events: number;
  measure_sec: number;
  memory_alloc_mb: number;
  memory_rss_mb: number;
  gc_next_mb: number;
  goroutines: number;
  mock_docs: number;
  mock_batches: number;
  mock_bytes_mb: number;
  mock_avg_batch: number;
  mock_docs_per_sec: number;
  output_acked: number;
  output_failed: number;
  output_batches: number;
  memory_total_mb: number;
  cpu_ticks: number;
  bytes_per_event: number;
  alloc_per_event: number;
  samples: Sample[];
}

export interface ScenarioCpuMetrics {
  base_eps: number[];
  pr_eps: number[];
  base_runs: RunEntry[];
  pr_runs: RunEntry[];
}

export interface SummaryEntry {
  base_avg: number;
  pr_avg: number;
  delta_pct: number;
}

export interface IndexRun {
  id: string;
  date: string;
  type: string;
  base_ref: string;
  pr_ref: string;
  pr_number?: number;
  pr_repo?: string;
  scenarios: string[];
  cpus: string[];
  summary: Record<string, Record<string, SummaryEntry>>;
}

export interface IndexData {
  runs: IndexRun[];
}

export interface RunDetailData {
  id: string;
  date: string;
  type: string;
  base_ref: string;
  pr_ref: string;
  pr_number?: number;
  pr_repo?: string;
  base_repo?: string;
  scenarios: Record<string, Record<string, ScenarioCpuMetrics>>;
}

export interface RunResponse {
  run_data: RunDetailData;
  index_entry: IndexRun;
}
