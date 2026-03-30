import { Line } from 'react-chartjs-2';
import { BASE_COLOR, PR_COLOR } from './ChartSetup';

interface Props {
  title: string;
  labels: string[];
  baseData: number[];
  prData: number[];
  yLabel: string;
}

export function TimeSeriesChart({ title, labels, baseData, prData, yLabel }: Props) {
  return (
    <div class="chart-wrap">
      <h3>{title}</h3>
      <Line
        data={{
          labels,
          datasets: [
            {
              label: 'Base',
              data: baseData,
              borderColor: BASE_COLOR,
              borderWidth: 2,
              pointRadius: 2,
              tension: 0.2,
              fill: false,
            },
            {
              label: 'PR',
              data: prData,
              borderColor: PR_COLOR,
              borderWidth: 2,
              pointRadius: 2,
              tension: 0.2,
              fill: false,
            },
          ],
        }}
        options={{
          responsive: true,
          maintainAspectRatio: true,
          interaction: { intersect: false, mode: 'index' as const },
          plugins: {
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const v = ctx.parsed.y ?? 0;
                  const formatted = yLabel === 'MB' ? v.toFixed(1) : v.toLocaleString();
                  return `${ctx.dataset.label}: ${formatted} ${yLabel}`;
                },
              },
            },
            legend: { position: 'top' as const },
          },
          scales: {
            y: {
              title: { display: true, text: yLabel },
              beginAtZero: false,
            },
            x: {
              title: { display: true, text: 'Elapsed' },
              grid: { display: false },
            },
          },
        }}
      />
    </div>
  );
}
