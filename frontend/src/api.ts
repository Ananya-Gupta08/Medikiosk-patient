const BASE=(import.meta.env.VITE_API_BASE_URL||'http://localhost:8000').trim().replace(/\/$/,'')
export class ApiError extends Error{constructor(public status:number,message:string){super(message)}}
async function request<T>(path:string,init?:RequestInit):Promise<T>{
  try{const response=await fetch(`${BASE}${path}`,{...init,credentials:'include',headers:{'Content-Type':'application/json',...init?.headers},cache:'no-store'});if(!response.ok){const body=await response.json().catch(()=>({}));throw new ApiError(response.status,body.detail||'Request failed')}return response.status===204?undefined as T:response.json()}
  catch(error){if(error instanceof ApiError)throw error;throw new ApiError(0,"We couldn't load your information right now.")}
}
export const api={get:<T>(p:string)=>request<T>(p),post:<T>(p:string,b?:unknown)=>request<T>(p,{method:'POST',body:b===undefined?undefined:JSON.stringify(b)}),put:<T>(p:string,b:unknown)=>request<T>(p,{method:'PUT',body:JSON.stringify(b)}),del:(p:string)=>request<void>(p,{method:'DELETE'})}
