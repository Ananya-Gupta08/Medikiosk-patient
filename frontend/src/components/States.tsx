import {AlertCircle,LoaderCircle} from 'lucide-react'
export function Loading(){return <div className="state" role="status"><LoaderCircle className="spin"/>Loading your information…</div>}
export function ErrorState({message,onRetry}:{message:string;onRetry?:()=>void}){return <div className="state error" role="alert"><AlertCircle/><p>{message}</p>{onRetry&&<button className="secondary" onClick={onRetry}>Try again</button>}</div>}
export function Empty({children}:{children:React.ReactNode}){return <p className="empty">{children}</p>}

