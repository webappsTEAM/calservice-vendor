import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiUrl = (env.VITE_WORKFORCE_API_URL || 'http://127.0.0.1:8001').replace('localhost', '127.0.0.1');

  return {
    plugins: [react()],
    server: {
      port: 5176,
      host: true,
      hmr: {
        clientPort: 5176,
      },
      proxy: {
        '/api': {
          target: apiUrl,
          changeOrigin: true,
          secure: false,
          timeout: 0,
          configure: (proxy) => {
            proxy.on('error', (err) => {
              if (err.code !== 'ECONNRESET') {
                console.warn('[Vite Proxy API]', err.message || err);
              }
            });
          },
        },
        '/media': {
          target: apiUrl,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});

