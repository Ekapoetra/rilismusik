import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { VerifiedBadge, SEAL_PATH } from './VerifiedBadge';

let root, container;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

test('renders an accessible seal with the shared path', async () => {
  await act(async () => root.render(<VerifiedBadge testid="seal" />));
  const svg = container.querySelector('[data-testid="seal"]');
  expect(svg.getAttribute('aria-label')).toBe('Terverifikasi');
  expect(svg.querySelector('path').getAttribute('d')).toBe(SEAL_PATH);
});

test('seal outline is a closed path', () => {
  expect(SEAL_PATH.startsWith('M')).toBe(true);
  expect(SEAL_PATH.endsWith('Z')).toBe(true);
});
