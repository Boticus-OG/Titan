// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-12-01',
  devtools: { enabled: true },
  ssr: false, // Disable SSR for now to simplify debugging

  // Runtime config for API URL
  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8000',
      wsBase: 'ws://localhost:8000',
    },
  },

  // CSS
  css: ['~/assets/css/main.css'],

  // Modules
  modules: [],

  // TypeScript
  typescript: {
    strict: true,
  },

  // Dev server proxy to backend
  vite: {
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: 'ws://localhost:8000',
          ws: true,
        },
      },
    },
  },
})
