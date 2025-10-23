import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/types': path.resolve(__dirname, './src/types'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/pages': path.resolve(__dirname, './src/pages'),
      '@/api': path.resolve(__dirname, './src/api'),
      '@/hooks': path.resolve(__dirname, './src/hooks'),
      '@/utils': path.resolve(__dirname, './src/utils'),
    },
  },
  server: {
    port: 3006,
    strictPort: true, // 端口被占用时报错，而不是自动切换到下一个端口
    proxy: {
      '/api': {
        target: 'http://localhost:8006',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    include: [
      'src/utils/**/__tests__/**/*.{test,spec}.{ts,tsx}',
      'src/services/**/__tests__/**/*.{test,spec}.{ts,tsx}'
    ],
    exclude: ['src/tests/e2e-*.test.ts', 'src/pages/__tests__/**', 'src/components/__tests__/**', 'tests/e2e/**', 'e2e/**'],
    pool: 'forks', // 使用 forks 而不是 threads 来避免 webidl-conversions 问题
    poolOptions: {
      forks: {
        singleFork: true, // 单进程运行测试，避免并发问题
      },
    },
  },
});

