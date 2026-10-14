import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import UpdatesPopup from './UpdatesPopup';
import { api } from '@/api/client';
import { useAuth } from '@/api/AuthContext';
import { useAppPreferences } from '@/contexts/AppPreferencesContext';
import { useNavigate } from 'react-router-dom';
import { APP_VERSION } from '@/version';

jest.mock('react-router-dom', () => ({ useNavigate: jest.fn() }), { virtual: true });
jest.mock('@/api/AuthContext', () => ({ useAuth: jest.fn() }));
jest.mock('@/api/client', () => ({ api: { post: jest.fn() } }));
jest.mock('@/contexts/AppPreferencesContext', () => ({ useAppPreferences: jest.fn() }));

const LABEL = { id: 'u1', role: 'label', email: 'l@t' };
let root, container, navigate;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  navigate = jest.fn();
  useNavigate.mockReturnValue(navigate);
  useAuth.mockReturnValue({ user: { ...LABEL } });
  useAppPreferences.mockReturnValue({ locale: 'id', t: (s) => s });
  api.post.mockResolvedValue({ data: { ok: true } });
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
const render = async () => { await act(async () => root.render(<UpdatesPopup />)); };

test('unseen label user gets the v popup', async () => {
  await render();
  expect(container.querySelector('[data-testid="updates-popup"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="updates-popup-title"]').textContent).toContain(`v${APP_VERSION}`);
});

test('already-seen version stays quiet', async () => {
  useAuth.mockReturnValue({ user: { ...LABEL, updates_seen_version: APP_VERSION } });
  await render();
  expect(container.querySelector('[data-testid="updates-popup"]')).toBeNull();
});

test('acknowledge posts seen once and closes', async () => {
  await render();
  await act(async () => container.querySelector('[data-testid="updates-popup-ok"]').click());
  expect(api.post).toHaveBeenCalledWith('/label/updates/seen', { version: APP_VERSION });
  expect(container.querySelector('[data-testid="updates-popup"]')).toBeNull();
});

test('see-more marks seen and opens the archive', async () => {
  await render();
  await act(async () => container.querySelector('[data-testid="updates-popup-more"]').click());
  expect(api.post).toHaveBeenCalledWith('/label/updates/seen', { version: APP_VERSION });
  expect(navigate).toHaveBeenCalledWith('/label/updates');
});

test('non-label users never see it', async () => {
  useAuth.mockReturnValue({ user: { id: 'a1', role: 'super_admin' } });
  await render();
  expect(container.querySelector('[data-testid="updates-popup"]')).toBeNull();
});
