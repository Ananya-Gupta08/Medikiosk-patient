import {useCallback,useEffect,useState} from 'react'
import {api} from './api'
export function useApi<T>(path:string){const [data,setData]=useState<T>();const [error,setError]=useState('');const [loading,setLoading]=useState(true);const load=useCallback(async()=>{setLoading(true);setError('');try{setData(await api.get<T>(path))}catch(e){setError(e instanceof Error?e.message:'Unable to load')}finally{setLoading(false)}},[path]);useEffect(()=>{void load()},[load]);return{data,error,loading,reload:load}}

