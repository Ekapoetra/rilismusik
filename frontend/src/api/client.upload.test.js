import axios from 'axios';
import { api } from './client';

function response(config, data) { return {config, data, status:200, statusText:'OK', headers:{}}; }
function form(size) { const value=new FormData();value.append('file',new File([new Uint8Array(size)],'cover.png',{type:'image/png'}));value.append('release_id','release');return value; }
afterEach(()=>jest.restoreAllMocks());
it('uploads large files without cookies or application credentials to the signed storage URL',async()=>{
  const configs=[];
  api.defaults.adapter=jest.fn(async config=>{
    configs.push(config);
    return response(config,config.url==='/uploads/initiate'?{upload_id:'upload',url:'https://storage.example.invalid/signed',content_type:'image/png'}:{saved:true});
  });
  const put=jest.spyOn(axios,'put').mockResolvedValue({status:200});
  const result=await api.post('/releases/cover',form(4*1024*1024),{params:{mode:'cover'},headers:{'Content-Type':'multipart/form-data'}});
  expect(put).toHaveBeenCalledWith('https://storage.example.invalid/signed',expect.any(File),expect.objectContaining({withCredentials:false,headers:{'Content-Type':'image/png'}}));
  expect(configs[0].url).toBe('/uploads/initiate');
  expect(JSON.parse(configs[0].data)).toMatchObject({target:'/releases/cover',fields:{release_id:'release'},query:{mode:'cover'}});
  expect(configs[1].url).toBe('/uploads/finalize');
  expect(configs[1].headers.get('Content-Type')).toBe('application/json');
  expect(configs[1].params).toBeUndefined();
  expect(JSON.parse(configs[1].data)).toEqual({upload_id:'upload'});
  expect(result.data).toEqual({saved:true});
});
it('keeps small uploads on the existing route',async()=>{
  const put=jest.spyOn(axios,'put').mockResolvedValue({status:200});
  api.defaults.adapter=jest.fn(async config=>response(config,{saved:true}));
  await api.post('/releases/cover',form(500),{headers:{'Content-Type':'multipart/form-data'}});
  expect(api.defaults.adapter.mock.calls[0][0].url).toBe('/releases/cover');
  expect(put).not.toHaveBeenCalled();
});
it('does not finalize after a storage upload fails',async()=>{
  const routes=[];
  api.defaults.adapter=jest.fn(async config=>{routes.push(config.url);return response(config,{upload_id:'upload',url:'https://storage.example.invalid/signed',content_type:'image/png'});});
  jest.spyOn(axios,'put').mockRejectedValue(new Error('upload interrupted'));
  await expect(api.post('/releases/cover',form(4*1024*1024))).rejects.toThrow('upload interrupted');
  expect(routes).toEqual(['/uploads/initiate']);
});
