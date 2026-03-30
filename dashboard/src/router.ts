import { useState, useEffect } from 'preact/hooks';

export interface Route {
  page: 'overview' | 'run';
  runId?: string;
}

function parseHash(): Route {
  const hash = window.location.hash.replace(/^#\/?/, '');
  const runMatch = hash.match(/^run\/(.+)$/);
  if (runMatch) {
    return { page: 'run', runId: runMatch[1] };
  }
  return { page: 'overview' };
}

export function navigate(path: string): void {
  window.location.hash = path;
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(parseHash());

  useEffect(() => {
    const handler = () => setRoute(parseHash());
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  return route;
}
