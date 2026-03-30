import { defineConfig } from 'vite'
import preact from '@preact/preset-vite'

export default defineConfig({
  plugins: [preact()],
  base: '/beats-bench/',
  server: {
    proxy: {
      '/data': {
        target: 'https://raw.githubusercontent.com/strawgate/beats-bench/bench-data',
        changeOrigin: true,
      },
    },
  },
})
