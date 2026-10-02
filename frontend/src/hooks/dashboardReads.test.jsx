import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { api } from '@/api/client';
import { resetSharedReads } from '@/api/sharedRead';
import { usePollingRead } from './usePollingRead';
import { useRoyaltyBalance } from './useRoyaltyBalance';
import { useLabelAnalytics } from './useLabelAnalytics';
jest.mock('@/api/client', () => ({ api: { get: jest.fn() } }));
jest.mock('@/api/AuthContext', () => ({ useAuth: () => ({user:{id:'u1'}}), formatApiError: (value) => String(value) }));
let root, container, latest;
const deferred=()=> { let resolve;const promise=new Promise(a=> {resolve=a;});return {promise,resolve}; };
function Probe({kind='poll',params={},seed,enabled=true}) {
  const poll=usePollingRead('/probe',params,{enabled:enabled && kind==='poll'});
  const balance=useRoyaltyBalance(enabled && kind==='balance',seed);
  const analytics=useLabelAnalytics({enabled:enabled && kind==='analytics',windowValue:params.window,labelId:params.label});
  latest=kind==='poll'?poll:kind==='balance'?balance:analytics;
  return <div>{JSON.stringify(latest)}</div>;
}
beforeEach(()=> {global.IS_REACT_ACT_ENVIRONMENT=true;jest.useFakeTimers();jest.clearAllMocks();resetSharedReads();container=document.createElement('div');document.body.appendChild(container);root=createRoot(container);Object.defineProperty(document,'visibilityState',{configurable:true,value:'visible'});api.get.mockResolvedValue({data:{value:100}});});
afterEach(async()=> {await act(async()=> root.unmount());container.remove();jest.useRealTimers();});
const render=async(props={})=> {await act(async()=> root.render(<Probe {...props}/>));};

test('polling shares StrictMode request and does not overlap slow response',async()=> {
  const first=deferred();api.get.mockReturnValue(first.promise);
  await act(async()=> root.render(<React.StrictMode><Probe/></React.StrictMode>));
  expect(api.get).toHaveBeenCalledTimes(1);
  await act(async()=> jest.advanceTimersByTime(45000));expect(api.get).toHaveBeenCalledTimes(1);
  await act(async()=> first.resolve({data:{value:25}}));expect(latest.data.value).toBe(25);
});
test('hidden tabs skip polling and refresh on return',async()=> {
  await render();expect(api.get).toHaveBeenCalledTimes(1);
  Object.defineProperty(document,'visibilityState',{configurable:true,value:'hidden'});
  await act(async()=> jest.advanceTimersByTime(45000));expect(api.get).toHaveBeenCalledTimes(1);
  Object.defineProperty(document,'visibilityState',{configurable:true,value:'visible'});
  await act(async()=> document.dispatchEvent(new Event('visibilitychange')));expect(api.get).toHaveBeenCalledTimes(2);
});
test('failed refresh preserves last value with error instead of zero',async()=> {
  await render();api.get.mockRejectedValue(new Error('offline'));
  await act(async()=> jest.advanceTimersByTime(15000));expect(latest.data.value).toBe(100);expect(latest.error).toBe(true);
});
test('late response for previous filter cannot overwrite current filter',async()=> {
  const old=deferred();api.get.mockReturnValueOnce(old.promise).mockResolvedValue({data:{value:200}});
  await render({params:{window:'6'}});await render({params:{window:'12'}});expect(latest.data.value).toBe(200);
  await act(async()=> old.resolve({data:{value:1}}));expect(latest.data.value).toBe(200);
});
test('dashboard seed avoids immediate duplicate balance read and refreshes later',async()=> {
  const seed={balance_available_idr:800};await render({kind:'balance',seed});
  expect(api.get).not.toHaveBeenCalled();expect(latest.balance).toEqual(seed);
  await act(async()=> window.dispatchEvent(new Event('focus')));expect(api.get).not.toHaveBeenCalled();
  await act(async()=> jest.advanceTimersByTime(15000));expect(api.get).toHaveBeenCalledWith('/withdraw/label/computed',{params:{}});
});
test('balance pages without dashboard seed still load immediately',async()=> {
  await render({kind:'balance'});expect(api.get).toHaveBeenCalledTimes(1);expect(latest.balance).toEqual({value:100});
});
test('analytics accepts independent six-month trend while main uses another filter',async()=> {
  await render({kind:'analytics',params:{window:'12',label:'a'}});
  expect(api.get).toHaveBeenLastCalledWith('/label/analytics',{params:{window:'12',label_id:'a'}});
  await render({kind:'analytics',params:{window:'6',label:'a'}});
  expect(api.get).toHaveBeenLastCalledWith('/label/analytics',{params:{window:'6',label_id:'a'}});
});
test('disabled reads cannot call financial endpoints',async()=> {
  await render({kind:'analytics',enabled:false});expect(api.get).not.toHaveBeenCalled();
});
