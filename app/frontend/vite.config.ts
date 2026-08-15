import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

const root = fileURLToPath(new URL('.', import.meta.url))
const directoryRoutes = ['/demo']

export default defineConfig({
  plugins: [
    {
      name: 'demo-directory-route',
      configureServer(server) {
        server.middlewares.use((request, response, next) => {
          const path = request.url?.split('?')[0]
          if (path !== undefined && directoryRoutes.includes(path)) {
            response.statusCode = 302
            response.setHeader('Location', `${path}/`)
            response.end()
            return
          }
          next()
        })
      },
    },
    react(),
  ],
  build: {
    rollupOptions: {
      input: {
        portfolio: resolve(root, 'index.html'),
        demo: resolve(root, 'demo/index.html'),
      },
    },
  },
  server: {
    proxy: {
      '/api': process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test-setup.ts',
    exclude: ['tests/e2e/**', 'node_modules/**', 'dist/**'],
  },
})
