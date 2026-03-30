import { Line } from 'react-chartjs-2';
import { PR_COLOR } from './ChartSetup';

interface Props {
  data: number[];
}

export function SparklineChart({ data }: Props) {
  return (
    <div style={{ height: '40px', width: '100%' }}>
      <Line
        data={{
          labels: data.map(() => ''),
          datasets: [
            {
              data,
              borderColor: PR_COLOR,
              borderWidth: 1.5,
              pointRadius: 0,
              tension: 0.3,
              fill: false,
            },
          ],
        }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
          scales: {
            x: { display: false },
            y: { display: false },
          },
        }}
      />
    </div>
  );
}
