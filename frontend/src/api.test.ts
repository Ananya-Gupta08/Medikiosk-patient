import {afterEach,describe,expect,it,vi} from 'vitest'
import {api,ApiError} from './api'

describe('patient API client',()=>{
  afterEach(()=>vi.unstubAllGlobals())
  it('uses no-store for sensitive patient requests',async()=>{
    const fetchMock=vi.fn().mockResolvedValue(new Response(JSON.stringify({ok:true}),{status:200,headers:{'Content-Type':'application/json'}}))
    vi.stubGlobal('fetch',fetchMock)
    await api.get('/api/me/dashboard')
    expect(fetchMock.mock.calls[0][1].cache).toBe('no-store')
  })
  it('turns backend errors into safe typed errors',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Safe message'}),{status:503,headers:{'Content-Type':'application/json'}})))
    await expect(api.get('/api/me/dashboard')).rejects.toEqual(expect.objectContaining<ApiError>({status:503,message:'Safe message'}))
  })
})
