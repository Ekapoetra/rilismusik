// Single source of truth: release/release.json (synced into src/release.json by
// scripts/sync-release.cjs). Format SemVer: MAYOR.MINOR.PATCH[-dev.N|-rc.N].
import release from "./release.json";

const SEMVER = /^(\d+)\.(\d+)\.(\d+)(?:-([a-z]+)\.(\d+))?$/;

export function describeVersion(version) {
  const m = SEMVER.exec(version) || [];
  const [, major = "0", minor = "0", patch = "0", stage, n] = m;
  const line = `${major}.${minor}`;
  const short = patch === "0" ? line : `${line}.${patch}`;
  return { line, label: stage ? `v${short} · ${stage} ${n}` : `v${short}` };
}

// Full build, e.g. "1.1.0-dev.1".
export const APP_BUILD = release.version;
// Release line used for the Updates batch / once-per-account popup ("1.1") —
// stays stable across dev builds so members aren't re-prompted every build.
export const APP_VERSION = describeVersion(APP_BUILD).line;
// Display label: "v1.1 · dev 1" while developing, "v1.1" once released.
export const APP_LABEL = describeVersion(APP_BUILD).label;
