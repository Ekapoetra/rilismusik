#!/usr/bin/env node
/* Satu sumber versi & catatan perubahan.
   Sumber : release/release.json (versi) + release/changelog.json (catatan per versi)
   Hasil  : frontend/src/release.json                         → version.js (APP_VERSION / APP_BUILD / APP_LABEL)
            prototype-rilis-musik/prototype-v13.0/release-data131.js → Studio Pratinjau & label versi prototype
            prototype-current.json (field "release")
   Pakai  : node scripts/sync-release.cjs          (tulis ulang hasil)
            node scripts/sync-release.cjs --check  (CI: gagal bila hasil tidak sinkron dengan sumber) */
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(root, p), 'utf8'));
const SEMVER = /^(\d+)\.(\d+)\.(\d+)(?:-(dev|rc)\.(\d+))?$/;
const STATUSES = new Set(['prototype', 'app', 'both']);

function fail(msg) { console.error(`sync-release: ${msg}`); process.exit(1); }

const release = read('release/release.json');
const changelog = read('release/changelog.json');

if (!SEMVER.test(release.version)) fail(`versi "${release.version}" bukan format MAYOR.MINOR.PATCH[-dev.N|-rc.N]`);
if (!Array.isArray(changelog) || !changelog.length) fail('changelog.json harus array berisi minimal satu versi');
if (changelog[0].version !== release.version) fail(`versi teratas changelog (${changelog[0].version}) harus sama dengan release.json (${release.version})`);
const ids = new Set();
for (const v of changelog) {
  if (!SEMVER.test(v.version)) fail(`versi changelog "${v.version}" tidak valid`);
  for (const e of v.entries || []) {
    if (!e.id || ids.has(e.id)) fail(`id entri kosong/duplikat: ${e.id}`);
    ids.add(e.id);
    if (!STATUSES.has(e.status)) fail(`status "${e.status}" pada ${e.id} harus prototype | app | both`);
    if (!e.title?.id || !e.title?.en) fail(`judul id/en wajib pada ${e.id}`);
    if (e.status !== 'app' && !e.where?.page) fail(`entri ${e.id} tampil di prototype — "where.page" wajib`);
  }
}

const header = '/* DIBANGKITKAN oleh scripts/sync-release.cjs dari release/*.json — jangan diedit langsung. */\n';
const outputs = {
  'frontend/src/release.json': JSON.stringify({ version: release.version, production: release.production }, null, 2) + '\n',
  'prototype-rilis-musik/prototype-v13.0/release-data131.js':
    header + `window.RM_RELEASE=${JSON.stringify(release)};\nwindow.RM_CHANGELOG=${JSON.stringify(changelog)};\n`,
};
const currentPath = 'prototype-current.json';
const current = read(currentPath);
current.release = release.version;
outputs[currentPath] = JSON.stringify(current, null, 2) + '\n';

const check = process.argv.includes('--check');
let stale = [];
for (const [rel, content] of Object.entries(outputs)) {
  const file = path.join(root, rel);
  const existing = fs.existsSync(file) ? fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n') : null;
  if (existing === content) continue;
  if (check) stale.push(rel); else { fs.writeFileSync(file, content); console.log(`ditulis: ${rel}`); }
}
if (check && stale.length) fail(`belum sinkron — jalankan "node scripts/sync-release.cjs": ${stale.join(', ')}`);
console.log(`release ${release.version} · ${changelog.length} versi · ${ids.size} entri${check ? ' · sinkron' : ''}`);
