import React from "react";
import { PanelLeft, Eye } from "lucide-react";

export const RoleNavPreview = ({ navigation = [], permissions = [], roleKey }) => {
  const perms = new Set(permissions);
  const isSuper = roleKey === "super_admin";
  const canSee = (item) => item.visible !== false && (isSuper || !item.permission || perms.has(item.permission));

  const parents = navigation.filter((item) => !item.parent_key);
  const childrenOf = (key) => navigation.filter((item) => item.parent_key === key);

  const rows = [];
  parents.forEach((parent) => {
    const kids = childrenOf(parent.key).filter(canSee);
    const parentVisible = canSee(parent);
    if (parentVisible || kids.length) {
      rows.push({ ...parent, isChild: false, muted: !parentVisible });
      kids.forEach((kid) => rows.push({ ...kid, isChild: true, muted: false }));
    }
  });

  return (
    <section className="rounded-lg border border-white/10 bg-white/[0.02] p-5" data-testid="admin-role-nav-preview">
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-500">
        <Eye className="h-4 w-4" /> Preview Menu Sidebar
      </div>
      <p className="mt-1 text-xs text-zinc-500">Menu yang akan tampil untuk role ini sesuai izin terpilih{isSuper ? " (Super Admin melihat semua menu)" : ""}.</p>
      <div className="mt-4 rounded-lg border border-white/10 bg-[#0B0915]/60 p-3">
        {rows.length === 0 ? (
          <div className="px-2 py-6 text-center text-sm text-zinc-600" data-testid="admin-role-nav-preview-empty">Belum ada menu yang tampil. Pilih izin untuk mengaktifkan menu.</div>
        ) : (
          <nav className="space-y-1">
            {rows.map((item) => (
              <div
                key={item.key}
                className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-sm ${item.isChild ? "ml-5 text-zinc-400" : "font-semibold text-zinc-200"} ${item.muted ? "opacity-50" : ""}`}
                data-testid={`admin-role-nav-preview-item-${item.key}`}
              >
                <PanelLeft className={`shrink-0 ${item.isChild ? "h-3 w-3" : "h-4 w-4"} text-zinc-500`} />
                <span className="truncate">{item.labels?.id || item.key}</span>
                {item.muted && <span className="ml-auto text-[10px] uppercase tracking-widest text-zinc-600">grup</span>}
              </div>
            ))}
          </nav>
        )}
      </div>
    </section>
  );
};
