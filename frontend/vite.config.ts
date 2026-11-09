import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev port can be overridden (e.g. PORT=5174) to run a branch preview next to the main app.
const port = Number(process.env.PORT) || 5173

export default defineConfig({
  plugins: [react()],
  server: {
    port,
    host: '0.0.0.0',
    hmr: {
      port,
      clientPort: port,
      overlay: false,
    },
    proxy: {
      '/api': {
        // BACKEND_URL lets the branch preview reach the backend from outside the compose network.
        target: process.env.BACKEND_URL || 'http://backend:8000',
        changeOrigin: true,
      },
    },
    headers: {
      // Force browser to always fetch fresh content from server
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    // Add cache busting for built assets
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]'
      }
    }
  },
  preview: {
    // Ensure preview server also has no-cache headers
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    }
  }
})
