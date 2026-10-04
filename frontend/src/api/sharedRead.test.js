import { sharedRead, resetSharedReads } from './sharedRead';
import { api } from './client';
jest.mock('./client', () => ({ api: { get: jest.fn() } }));
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return { promise, resolve, reject }; };
beforeEach(() => { resetSharedReads(); jest.clearAllMocks(); });

test('same account/filter shares one active request, then reads fresh', async () => {
  const first=deferred(); api.get.mockReturnValueOnce(first.promise).mockResolvedValue({data:2});
  const a=sharedRead('u1','/label/analytics',{window:'6',label_id:'a'});
  const b=sharedRead('u1','/label/analytics',{label_id:'a',window:'6'});
  expect(a).toBe(b); expect(api.get).toHaveBeenCalledTimes(1);
  first.resolve({data:1}); await a;
  expect(await sharedRead('u1','/label/analytics',{window:'6',label_id:'a'})).toEqual({data:2});
  expect(api.get).toHaveBeenCalledTimes(2);
});
test('account, label and window cannot share a request', async () => {
  api.get.mockImplementation(() => new Promise(() => {}));
  const first=sharedRead('u1','/label/analytics',{window:'6',label_id:'a'});
  for (const [user,params] of [['u2',{window:'6',label_id:'a'}],['u1',{window:'12',label_id:'a'}],['u1',{window:'6',label_id:'b'}]])
    expect(sharedRead(user,'/label/analytics',params)).not.toBe(first);
  expect(api.get).toHaveBeenCalledTimes(4);
});
test('failed requests can be retried and auth resets isolate late completion', async () => {
  const first=deferred(), second=deferred(); api.get.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise).mockRejectedValue(new Error('offline'));
  const a=sharedRead('u1','/label/dashboard'); resetSharedReads(); const b=sharedRead('u1','/label/dashboard');
  first.resolve({data:'old'}); await a;
  expect(sharedRead('u1','/label/dashboard')).toBe(b);
  second.reject(new Error('offline')); await expect(b).rejects.toThrow('offline');
  await expect(sharedRead('u1','/label/dashboard')).rejects.toThrow('offline');
  expect(api.get).toHaveBeenCalledTimes(3);
});
