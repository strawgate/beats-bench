import { render } from 'preact';
import { Dashboard } from '@benchkit/chart';
import '@benchkit/chart/css';
import './style.css';

const source = {
  owner: 'strawgate',
  repo: 'beats-bench',
};

function App() {
  return (
    <div class="page-shell">
      <header class="site-header">
        <h1>beats-bench</h1>
        <p>
          Filebeat pipeline benchmark results — tracking processor throughput
          and resource usage across commits
        </p>
        <div class="header-links">
          <a href="https://github.com/strawgate/beats-bench">Repository</a>
          <a href="https://github.com/strawgate/beats-bench/actions/workflows/bench.yml">
            Run Benchmark
          </a>
        </div>
      </header>

      <Dashboard
        source={source}
        labels={{
          heroTitle: 'Benchmark Overview',
        }}
        regressionThreshold={5}
        regressionWindow={5}
        maxRuns={30}
        maxPoints={20}
        metricLabelFormatter={(metric) => {
          const friendly: Record<string, string> = {
            'events_s': 'Events / sec',
          };
          return friendly[metric] ?? metric.replace(/_/g, ' ');
        }}
        commitHref={(sha) =>
          `https://github.com/elastic/beats/commit/${sha}`
        }
      />
    </div>
  );
}

render(<App />, document.getElementById('app')!);
