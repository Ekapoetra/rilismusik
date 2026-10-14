import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import JourneySteps from './JourneySteps';
import { FileText, Send, Clock3, CheckCircle2 } from 'lucide-react';

const STEPS = [
  { key: 'a', label: 'Draft', icon: FileText },
  { key: 'b', label: 'Diajukan', icon: Send },
  { key: 'c', label: 'Review', icon: Clock3 },
  { key: 'd', label: 'Tayang', icon: CheckCircle2 },
];
let root, container;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
const stateOf = (key) => container.querySelector(`[data-testid="jp-step-${key}"]`)?.dataset.state;

test('current position marks done/current/upcoming', async () => {
  await act(async () => root.render(<JourneySteps steps={STEPS} current={1} testPrefix="jp" />));
  expect(stateOf('a')).toBe('done');
  expect(stateOf('b')).toBe('current');
  expect(stateOf('c')).toBe('upcoming');
  expect(stateOf('d')).toBe('upcoming');
  expect(container.querySelector('[data-testid="jp-here"]')).toBeTruthy();
});

test('terminal replaces the last node and finishes the rest', async () => {
  await act(async () => root.render(<JourneySteps steps={STEPS} current={1} terminal="Ditolak" testPrefix="jp" />));
  expect(stateOf('a')).toBe('done');
  expect(stateOf('b')).toBe('done');
  expect(stateOf('c')).toBe('done');
  expect(stateOf('d')).toBe('terminal');
  expect(container.querySelector('[data-testid="jp-here"]')).toBeNull();
});
