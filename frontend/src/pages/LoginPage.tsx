import {FormEvent,useState} from 'react'
import {HeartPulse,LogIn} from 'lucide-react'
import {api} from '../api'

type Patient={id:string;name:string}

export function LoginPage({onLogin}:{onLogin:(patient:Patient)=>void}){
  const [abha,setAbha]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('')
  async function submit(event:FormEvent){event.preventDefault();setError('');setBusy(true);try{const result=await api.post<{patient:Patient}>('/api/auth/login',{abha_number:abha});onLogin(result.patient)}catch(cause){setError(cause instanceof Error?cause.message:'We could not sign you in.')}finally{setBusy(false)}}
  return <main className="login-page"><section className="login-card"><HeartPulse className="login-icon" aria-hidden="true"/><h1>Patient sign in</h1><p>Enter the ABHA number registered by your hospital.</p><form onSubmit={submit}><label htmlFor="abha-number">ABHA number</label><input id="abha-number" inputMode="numeric" autoComplete="off" value={abha} onChange={event=>setAbha(event.target.value)} placeholder="XX-XXXX-XXXX-XXXX" minLength={14} maxLength={24} required/><button className="primary wide" disabled={busy}><LogIn/>{busy?'Signing in…':'Sign in'}</button></form>{error&&<p className="form-error" role="alert">{error}</p>}<p className="demo-warning"><strong>Demo access:</strong> ABHA OTP verification must be connected before production use.</p></section></main>
}
