import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 开发时把 /api 请求代理到本地 FastAPI(8000)，绕开 CORS
export default defineConfig({
  // 相对 base：构建产物可直接放到 GitHub Pages 子路径（org.github.io/<repo>/）
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
