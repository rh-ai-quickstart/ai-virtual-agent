import { TanStackRouterVite } from '@tanstack/router-plugin/vite';
import react from '@vitejs/plugin-react-swc';
import path from 'path';
import { defineConfig } from 'vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    // Please make sure that '@tanstack/router-plugin' is passed before '@vitejs/plugin-react'
    TanStackRouterVite({ target: 'react', autoCodeSplitting: true }),
    react(),
    // ...,
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'), // This line maps '@/' to your 'src' directory
      // You might have other aliases too
    },
  },
  server: {
    host: '0.0.0.0', // Enable container access
    port: 5173,
    watch: {
      usePolling: true, // Enable polling for container file watching
      interval: 1000, // Check every second
    },
    hmr: {
      port: 5173,
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
  build: { chunkSizeWarningLimit: 2000 },
});
