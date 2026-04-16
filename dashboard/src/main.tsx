import { render } from 'preact';
import { useState, useEffect } from 'preact/hooks';
import { Dashboard, RunDashboard } from '@benchkit/chart';
import type { DataSource } from '@benchkit/chart';
import '@benchkit/chart/css';
import './style.css';

const source: DataSource = {
  owner: 'strawgate',
  repo: 'beats-bench',
};

type Route = { page: 'overview' } | { page: 'runs' };

function parseHash(): Route {
  const hash = window.location.hash.replace(/^#\/?/, '');
  if (hash === 'runs' || hash.startsWith('runs')) {
    return { page: 'runs' };
  }
  return { page: 'overview' };
}

function App() {
  const [route, setRoute] = useState<Route>(parseHash());

  useEffect(() => {
    const handler = () => setRoute(parseHash());
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  const commitHref = (sha: string) =>
    `https://github.com/elastic/beats/commit/${sha}`;

  const metricLabel = (metric: string) => {
    const friendly: Record<string, string> = {
      'events_s': 'Events / sec',
    };
    return friendly[metric] ?? metric.replace(/_/g, ' ');
  };

  return (
    <div class="page-shell">
      <header class="site-header">
        <h1>beats-bench</h1>
        <p>
          Filebeat pipeline benchmark results — tracking processor throughput
          and resource usage across commits
        </p>
        <nav class="header-links">
          <a href="#/">Overview</a>
          <a href="#/runs">Run Comparison</a>
          <a href="https://github.com/strawgate/beats-bench">Repository</a>
          <a href="https://github.com/strawgate/beats-bench/actions/workflows/bench.yml">
            Run Benchmark
          </a>
        </nav>
      </header>

      {route.page === 'runs' ? (
        <RunDashboard
          source={source}
          defaultBranch="main"
          regressionThreshold={5}
          commitHref={commitHref}
          metricLabelFormatter={metricLabel}
        />
      ) : (
        <Dashboard
          source={source}
          labels={{
            heroTitle: 'Benchmark Overview',
          }}
          regressionThreshold={5}
          regressionWindow={5}
          maxRuns={30}
          maxPoints={20}
          metricLabelFormatter={metricLabel}
          commitHref={commitHref}
        />
      )}
    </div>
  );
}

render(<App />, document.getElementById('app')!);
