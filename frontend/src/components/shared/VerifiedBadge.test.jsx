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
  const path = svg.querySelector('path');
  expect(path.getAttribute('d')).toBe(SEAL_PATH);
  expect(path.getAttribute('fill-rule')).toBe('evenodd');
  expect(svg.querySelectorAll('path')).toHaveLength(1);
});

test("seal has the star outline plus a knocked-out check", () => {
  expect(SEAL_PATH.startsWith('M')).toBe(true);
  expect(SEAL_PATH.endsWith("Z")).toBe(true);
  expect(SEAL_PATH.match(/M/g)).toHaveLength(2); // star + check hole
});
