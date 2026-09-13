import {ChangeEvent,FormEvent,useState} from 'react'
import {Download,Edit3,FileUp,RefreshCw,Save,X} from 'lucide-react'
import {api,apiUrl} from '../api'
import {useApi} from '../hooks'
import {UploadedRecord} from '../types'
import {Empty,ErrorState,Loading} from './States'

const MAX_UPLOAD_BYTES=4*1024*1024
const groups=[['Important information','important_points'],['Medicines mentioned','medicines_mentioned'],['Test results','test_results'],['Follow-up actions','follow_up_actions']] as const

export function UploadedRecords(){
  const {data,error,loading,reload}=useApi<UploadedRecord[]>('/api/me/uploaded-records')
  const [file,setFile]=useState<File>()
  const [busy,setBusy]=useState(false)
  const [message,setMessage]=useState('')
  const [editing,setEditing]=useState<string>()
  const [summary,setSummary]=useState('')

  function choose(event:ChangeEvent<HTMLInputElement>){
    const selected=event.target.files?.[0]
    if(selected&&selected.size>MAX_UPLOAD_BYTES){setFile(undefined);setMessage('Please choose a file smaller than 4 MB.');event.target.value='';return}
    setFile(selected);setMessage('')
  }
  async function upload(event:FormEvent<HTMLFormElement>){
    event.preventDefault();if(!file)return
    const form=event.currentTarget
    setBusy(true);setMessage('')
    try{
      const record=await api.upload<UploadedRecord>('/api/me/uploaded-records',file)
      setFile(undefined);form.reset()
      setMessage(record.extraction_status==='complete'?'Record uploaded and important information extracted.':'Record uploaded, but extraction is unavailable. You can retry.')
      await reload()
    }catch(cause){setMessage(cause instanceof Error?cause.message:'The record could not be uploaded.')}finally{setBusy(false)}
  }
  async function retry(id:string){setBusy(true);setMessage('');try{const record=await api.post<UploadedRecord>(`/api/me/uploaded-records/${id}/extract`);setMessage(record.extraction_status==='complete'?'Important information extracted.':'Extraction is unavailable right now. Please retry later.');await reload()}catch(cause){setMessage(cause instanceof Error?cause.message:'Extraction could not be retried.')}finally{setBusy(false)}}
  async function save(event:FormEvent,id:string){event.preventDefault();if(!summary.trim())return;setBusy(true);setMessage('');try{await api.put(`/api/me/uploaded-records/${id}`,{history:summary.trim()});setEditing(undefined);setMessage('Your corrected summary was saved.');await reload()}catch(cause){setMessage(cause instanceof Error?cause.message:'Your changes could not be saved.')}finally{setBusy(false)}}

  return <section className="uploads" aria-labelledby="upload-heading">
    <h2 id="upload-heading">Add a medical record</h2>
    <form className="upload-form" onSubmit={upload}>
      <label htmlFor="medical-upload">Choose a medical record</label>
      <input id="medical-upload" type="file" accept="application/pdf,text/plain,image/jpeg,image/png,image/webp" onChange={choose}/>
      <p className="note">PDF, text, JPEG, PNG or WebP. Maximum 4 MB. Please check the AI-extracted information against the original record.</p>
      <button className="primary wide" disabled={busy||!file}><FileUp aria-hidden="true"/>{busy?'Working…':'Upload and extract'}</button>
    </form>
    {message&&<p className="upload-message" role="status">{message}</p>}
    <h2>Your uploaded records</h2>
    {loading?<Loading/>:error||!data?<ErrorState message={error} onRetry={reload}/>:!data.length?<Empty>No records have been uploaded yet.</Empty>:<div className="uploaded-list">{data.map(item=><article className="record uploaded" key={item.id}>
      <div className="record-row"><div><h3>{item.extracted_data?.title||item.file_name}</h3><p>{new Date(item.created_at).toLocaleDateString()} · {(item.file_size/1024).toFixed(0)} KB</p></div><span className={`extract-status ${item.extraction_status}`}>{item.extraction_status==='complete'?'Extracted':item.extraction_status==='failed'?'Needs retry':'Processing'}</span></div>
      {item.extraction_status==='failed'&&<button className="secondary" disabled={busy} onClick={()=>void retry(item.id)}><RefreshCw aria-hidden="true"/>Retry extraction</button>}
      {item.extracted_data&&<>{editing===item.id?<form className="history-form" onSubmit={event=>void save(event,item.id)}><label htmlFor={`uploaded-summary-${item.id}`}>Edit your summary</label><textarea id={`uploaded-summary-${item.id}`} rows={7} maxLength={10000} value={summary} onChange={event=>setSummary(event.target.value)} disabled={busy}/><div className="form-actions"><button className="primary" disabled={busy||!summary.trim()}><Save aria-hidden="true"/>Save</button><button type="button" className="secondary" onClick={()=>setEditing(undefined)}><X aria-hidden="true"/>Cancel</button></div></form>:<><p className="record-summary">{item.patient_summary||item.extracted_data.summary}</p>{groups.map(([label,key])=>item.extracted_data?.[key]?.length?<div className="extracted-group" key={key}><strong>{label}</strong><ul>{item.extracted_data[key].map((point,index)=><li key={`${key}-${index}`}>{point}</li>)}</ul></div>:null)}<div className="form-actions"><button className="secondary" onClick={()=>{setEditing(item.id);setSummary(item.patient_summary||item.extracted_data!.summary)}}><Edit3 aria-hidden="true"/>Edit summary</button><a className="secondary link" href={apiUrl(`/api/me/uploaded-records/${item.id}/file`)}><Download aria-hidden="true"/>Download original</a></div></>}</>}
    </article>)}</div>}
  </section>
}
