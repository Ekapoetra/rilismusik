# Prototype Rilis Musik branch

This branch contains the user's V13.0 prototype handoff in `prototype-rilis-musik/`.
Read `PROTOTYPE-RILIS-MUSIK.txt`, then the handoff's `START-HERE.txt`, `CONTEXT.txt`, `PARKED.txt` and `visual-references/READ-ME.txt`.

The current prototype is `prototype-rilis-musik/prototype-v13.0/`; older version numbers in historical notes are not the baseline. Run it from `prototype-rilis-musik/` using `npm run preview`. Confirm V13.0 in the actual browser preview.

Root `backend/` and `frontend/` are the existing application's code inherited from main. The handoff's `reference-code/` and `context-history/` are read-only historical evidence. Any separately supplied `sources/` directory is read-only synced reference material.

The entire office/background 3D concept is cancelled. Token prices/conversion, emblem decisions, final package prices/quotas and other parked proposals are not approved implementation instructions. Preserve existing rights, data and permissions. Do not infer production readiness from prototype test results or user visual approval from historical screenshots.

The first Devin task is to run the baseline, expose a preview, compare the latest UI requirements and show concise findings with screenshots. No production migration, merge or deployment is authorized by the handoff. The upload was explicitly requested by the user; future implementation scope follows the user's next instruction. Communicate concisely in Indonesian.

DEPLOYMENT SAFETY (hard rule): never run `vercel --prod`, `vercel promote`, or `vercel rollback` — the production domain (www.rilismusik.com) is served from the `main` branch only. Previews come free: every `git push` to `prototype-node-api` triggers a preview deployment automatically (URL pattern: rilismusik-git-prototype-node-api-ekapoetras-projects.vercel.app). If a CLI deploy is ever needed, use plain `vercel` (preview) — never flags that touch production aliases.
