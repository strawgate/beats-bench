import { defineConfig } from 'vite'
import preact from '@preact/preset-vite'

export default defineConfig({
  plugins: [preact()],
  base: '/beats-bench/',
  server: {
    proxy: {
      '/beats-bench/data': {
        target: 'http://localhost:4173',
        rewrite: (path) => path.replace('/beats-bench/data', '/data'),
      },
    },
  },
})
