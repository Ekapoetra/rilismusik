import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LabelKycProvider, useLabelKyc } from './LabelKycContext';
import { api } from '@/api/client';
import { resetSharedReads } from '@/api/sharedRead';
let mockPath, mockUser;
jest.mock('react-router-dom',()=> ({useLocation:()=> ({pathname:mockPath})}),{virtual:true});
jest.mock('@/api/AuthContext',()=> ({useAuth:()=> ({user:mockUser})}));
jest.mock('@/api/client',()=> ({api:{get:jest.fn()}}));
let root, container, seen;
function Child(){seen.push(useLabelKyc());return null;}
const deferred=()=> {let resolve;const promise=new Promise(a=> {resolve=a;});return {promise,resolve};};
beforeEach(()=> {global.IS_REACT_ACT_ENVIRONMENT=true;jest.clearAllMocks();resetSharedReads();mockPath='/label/dashboard';mockUser={id:'u1',active_label_id:'a'};seen=[];container=document.createElement('div');document.body.appendChild(container);root=createRoot(container);});
afterEach(async()=> {await act(async()=>root.unmount());container.remove();});
const render=async()=> {await act(async()=>root.render(<LabelKycProvider><Child/><Child/></LabelKycProvider>));};
test('layout and dashboard consumers share one verified state/read',async()=> {
 api.get.mockResolvedValue({data:{is_verified:true}});await render();
 expect(api.get).toHaveBeenCalledTimes(1);expect(seen.at(-1).kyc.is_verified).toBe(true);
 await act(async()=>window.dispatchEvent(new CustomEvent('rilismusik:kyc-updated',{detail:{is_verified:false}})));
 expect(seen.at(-1).kyc.is_verified).toBe(false);
});
test('KYC network error cannot grant verified access',async()=> {
 api.get.mockRejectedValue(new Error('offline'));await render();expect(seen.at(-1).kyc).toBeNull();expect(seen.at(-1).error).toBe(true);
});
test('active-label switch hides former verification before new response',async()=> {
 const second=deferred();api.get.mockResolvedValueOnce({data:{is_verified:true}}).mockReturnValueOnce(second.promise);
 await render();mockUser={...mockUser,active_label_id:'b'};seen=[];await render();
 expect(seen.every(value=> value.kyc===null)).toBe(true);
 await act(async()=>second.resolve({data:{is_verified:false}}));expect(seen.at(-1).kyc.is_verified).toBe(false);
});
