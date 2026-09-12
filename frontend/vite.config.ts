import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({mode}) => { const env=loadEnv(mode,process.cwd(),''); const appName=env.VITE_APP_NAME||'Patient Care'; return ({
  plugins: [react(), tailwindcss(), VitePWA({
    registerType: 'autoUpdate',
    includeAssets: ['icon.svg'],
    manifest: { name: appName, short_name: appName, description: 'Your medicines, visits, and health check-ins', theme_color: '#0f766e', background_color: '#f7faf9', display: 'standalone', start_url: '/', icons: [{src:'/icon.svg',sizes:'any',type:'image/svg+xml',purpose:'any maskable'}]},
    workbox: { navigateFallback: '/index.html', importScripts: ['push-handler.js'], runtimeCaching: [{urlPattern: ({url}) => url.pathname.startsWith('/api/'), handler: 'NetworkOnly'}] }
  })]
})})
