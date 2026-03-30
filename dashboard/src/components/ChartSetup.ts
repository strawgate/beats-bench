import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

export const BASE_COLOR = 'rgb(37, 99, 235)';
export const BASE_COLOR_BG = 'rgba(37, 99, 235, 0.3)';
export const PR_COLOR = 'rgb(22, 163, 74)';
export const PR_COLOR_BG = 'rgba(22, 163, 74, 0.3)';
