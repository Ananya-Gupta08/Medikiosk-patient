import React from 'react';import ReactDOM from 'react-dom/client';import App from './App';import './styles.css';import {registerSW} from 'virtual:pwa-register'
document.title=import.meta.env.VITE_APP_NAME||'Patient Care'
registerSW({onNeedRefresh(){/* Update is offered on the next navigation in this MVP. */}})
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
