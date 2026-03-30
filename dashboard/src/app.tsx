import { useRoute } from './router';
import { Overview } from './pages/Overview';
import { RunDetail } from './pages/RunDetail';

export function App() {
  const route = useRoute();
  if (route.page === 'run' && route.runId) {
    return <RunDetail runId={route.runId} />;
  }
  return <Overview />;
}
