import { Bar } from 'react-chartjs-2';
import { BASE_COLOR, BASE_COLOR_BG, PR_COLOR, PR_COLOR_BG } from './ChartSetup';

interface Props {
  labels: string[];
  baseAvgs: number[];
  prAvgs: number[];
}

export function EPSBarChart({ labels, baseAvgs, prAvgs }: Props) {
  return (
    <Bar
      data={{
        labels,
        datasets: [
          {
            label: 'Base EPS',
            data: baseAvgs,
            backgroundColor: BASE_COLOR_BG,
            borderColor: BASE_COLOR,
            borderWidth: 2,
          },
          {
            label: 'PR EPS',
            data: prAvgs,
            backgroundColor: PR_COLOR_BG,
            borderColor: PR_COLOR,
            borderWidth: 2,
          },
        ],
      }}
      options={{
        responsive: true,
        interaction: { intersect: false, mode: 'index' as const },
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const y = ctx.parsed.y ?? 0;
                return `${ctx.dataset.label}: ${y.toLocaleString()} events/sec`;
              },
            },
          },
        },
        scales: {
          y: {
            title: { display: true, text: 'Events/sec' },
            beginAtZero: false,
          },
          x: {
            grid: { display: false },
          },
        },
      }}
    />
  );
}
