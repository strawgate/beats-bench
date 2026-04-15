import { render } from 'preact';
import { Dashboard } from '@benchkit/chart';
import '@benchkit/chart/css';

const source = {
  owner: 'strawgate',
  repo: 'beats-bench',
};

render(
  <Dashboard
    source={source}
    labels={{
      brand: 'beats-bench',
      heroTitle: 'Filebeat Pipeline Benchmarks',
    }}
    regressionThreshold={5}
    regressionWindow={5}
    maxRuns={30}
    commitHref={(sha) =>
      `https://github.com/elastic/beats/commit/${sha}`
    }
  />,
  document.getElementById('app')!,
);
