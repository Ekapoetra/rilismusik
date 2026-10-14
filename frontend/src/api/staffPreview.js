// D10 — Staff access preview (read-only impersonation for Super Admin).
// Module-level store so the axios interceptor can check it without React.

let preview = null;
const listeners = new Set();

export function getStaffPreview() {
  return preview;
}

export function staffPreviewActive() {
  return !!preview;
}

export function startStaffPreview(staff) {
  preview = staff;
  listeners.forEach((fn) => fn(preview));
}

export function exitStaffPreview() {
  preview = null;
  listeners.forEach((fn) => fn(null));
}

// Super Admin privileges are suspended while previewing a staff member's
// access, so super-only UI must hide exactly as it would for that staff user.
export function isSuperEffective(user) {
  return user?.role === "super_admin" && !preview;
}

export function subscribeStaffPreview(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
