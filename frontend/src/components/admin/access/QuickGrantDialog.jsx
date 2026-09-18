import React, { useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { ShieldCheck } from "lucide-react";

export const QuickGrantDialog = ({ open, onClose, pending, roles, onGranted }) => {
  const grantable = useMemo(() => (roles || []).filter((r) => !r.builtin && r.active !== false), [roles]);
  const [roleId, setRoleId] = useState("");
  const [picked, setPicked] = useState(() => (pending || []).map((p) => p.key));
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (open) { setPicked((pending || []).map((p) => p.key)); setRoleId(grantable[0]?.id || ""); } }, [open, pending, grantable]);

  const toggle = (key) => setPicked((cur) => cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key]);
  const grant = async () => {
    const role = grantable.find((r) => r.id === roleId);
    if (!role || picked.length === 0) return;
    setSaving(true);
    try {
      const merged = Array.from(new Set([...(role.permissions || []), ...picked]));
      await api.patch(`/admin/access/roles/${role.id}`, { permissions: merged });
      toast.success(`${picked.length} izin diberikan ke “${role.name}”.`);
      onGranted && (await onGranted());
      onClose();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="ui-menu max-h-[90dvh] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-lg" data-testid="quick-grant-dialog">
        <DialogHeader>
          <DialogTitle>Berikan Izin ke Role</DialogTitle>
          <DialogDescription>Tetapkan izin baru langsung ke sebuah role tanpa membuka editor. Super Admin sudah otomatis memilikinya.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <label className="block">
            <span className="rm-label">Role tujuan</span>
            <select className="rm-input" value={roleId} onChange={(e) => setRoleId(e.target.value)} data-testid="quick-grant-role-select">
              {grantable.length === 0 && <option value="">Tidak ada role kustom aktif</option>}
              {grantable.map((r) => <option key={r.id} value={r.id}>{r.name} · {r.permissions?.length || 0} izin</option>)}
            </select>
          </label>
          <div>
            <span className="rm-label">Izin yang akan diberikan</span>
            <div className="mt-1 space-y-1.5">
              {(pending || []).map((p) => (
                <label key={p.key} className="flex cursor-pointer items-center gap-2 rounded-md border border-white/10 bg-white/[0.02] px-3 py-2 text-sm" data-testid={`quick-grant-perm-${p.key.replaceAll(".", "-")}`}>
                  <input type="checkbox" checked={picked.includes(p.key)} onChange={() => toggle(p.key)} className="h-4 w-4 accent-emerald-500" />
                  <span className="text-zinc-200">{p.label_id}</span>
                  {(p.destructive || p.sensitive) && <span className={`ml-auto rounded px-1.5 py-0.5 text-[10px] font-bold ${p.destructive ? "bg-red-500/15 text-red-300" : "bg-amber-500/15 text-amber-300"}`}>{p.destructive ? "Destruktif" : "Sensitif"}</span>}
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" className="rm-btn-ghost text-sm" onClick={onClose} data-testid="quick-grant-cancel">Batal</button>
            <button type="button" className="rm-btn-primary inline-flex items-center gap-2 text-sm" disabled={saving || !roleId || picked.length === 0} onClick={grant} data-testid="quick-grant-submit"><ShieldCheck className="h-4 w-4" />{saving ? "Menyimpan…" : `Berikan (${picked.length})`}</button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
