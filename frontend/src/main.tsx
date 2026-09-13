import React from 'react';import ReactDOM from 'react-dom/client';import App from './App';import './styles.css';import './auth.css';import './uploads.css';import {registerSW} from 'virtual:pwa-register'
document.title=import.meta.env.VITE_APP_NAME||'Patient Care'
registerSW({immediate:true})
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
