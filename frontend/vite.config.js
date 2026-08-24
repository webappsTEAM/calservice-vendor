import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiUrl = env.VITE_WORKFORCE_API_URL || 'http://127.0.0.1:8001';

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
          ws: true,
          timeout: 0,
          proxyTimeout: 0,
          configure: (proxy) => {
            proxy.on('error', (err, req, res) => {
              if (['ECONNRESET', 'ECONNREFUSED', 'EPIPE', 'ETIMEDOUT'].includes(err.code) || err.message?.includes('ECONNRESET')) {
                return;
              }
              console.warn('[vite proxy error]', req?.url, err.message);
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

