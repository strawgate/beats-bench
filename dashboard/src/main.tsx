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
      title: 'Filebeat Pipeline Benchmarks',
      subtitle: 'Automated throughput and resource tracking for Elastic Filebeat pipelines',
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
