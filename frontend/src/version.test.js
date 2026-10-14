import { describeVersion, APP_BUILD, APP_VERSION, APP_LABEL } from './version';

test('dev builds keep the release line and show the dev number', () => {
  expect(describeVersion('1.1.0-dev.1')).toEqual({ line: '1.1', label: 'v1.1 · dev 1' });
  expect(describeVersion('1.1.0-rc.2')).toEqual({ line: '1.1', label: 'v1.1 · rc 2' });
});

test('released versions drop a zero patch, keep a real one', () => {
  expect(describeVersion('1.1.0')).toEqual({ line: '1.1', label: 'v1.1' });
  expect(describeVersion('1.1.3')).toEqual({ line: '1.1', label: 'v1.1.3' });
});

test('exports come from release.json', () => {
  expect(APP_BUILD).toMatch(/^\d+\.\d+\.\d+/);
  expect(APP_VERSION).toBe(describeVersion(APP_BUILD).line);
  expect(APP_LABEL).toBe(describeVersion(APP_BUILD).label);
});
