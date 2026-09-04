import React, { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { DndContext, PointerSensor, useSensor, useSensors, closestCenter } from "@dnd-kit/core";
import { SortableContext, arrayMove, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { api, formatApiError } from "@/api/client";
import { SortableNavRow } from "@/components/admin/ui/SortableNavRow";
import { useAdminNavigation } from "@/contexts/AdminNavigationContext";
import { toast } from "@/components/ui/sonner";
import { useAuth } from "@/api/AuthContext";

export default function UiSettings() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("ui.settings.manage");
  const { reload } = useAdminNavigation(); const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));
  useEffect(() => { api.get("/admin/ui-settings").then(({ data }) => setForm(data)).catch((requestError) => setError(formatApiError(requestError.response?.data?.detail))); }, []);
  if (!form) return <div className="py-20 text-center text-sm text-zinc-500" data-testid="admin-ui-settings-loading">Memuat pengaturan UI…</div>;
  const updateItem = (next) => setForm({ ...form, items: form.items.map((item) => item.key === next.key ? next : item) });
  const onDragEnd = ({ active, over }) => { if (!canManage || !over || active.id === over.id) return; const oldIndex = form.items.findIndex((item) => item.key === active.id); const newIndex = form.items.findIndex((item) => item.key === over.id); setForm({ ...form, items: arrayMove(form.items, oldIndex, newIndex) }); };
  const save = async () => { setSaving(true); setError(""); try { const payload = { default_locale: form.default_locale, items: form.items.map(({ permission, icon, ...item }, index) => ({ ...item, order: index })) }; const { data } = await api.put("/admin/ui-settings", payload); setForm(data); await reload(); toast.success("Urutan, subtab, dan bahasa navigasi disimpan."); } catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); } finally { setSaving(false); } };
  return <div className="space-y-7" data-testid="admin-ui-settings-page"><header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-6"><div><div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Admin UI</div><h1 className="mt-1 font-display text-4xl font-extrabold">Bahasa & Navigasi</h1><p className="mt-2 text-sm text-zinc-400">Tarik untuk mengubah urutan. Pilih parent untuk menjadikan halaman sebagai subtab internal.</p></div><div className="flex flex-wrap items-end gap-3"><label><span className="rm-label">Bahasa Bawaan</span><select className="rm-input min-w-36" value={form.default_locale} disabled={!canManage} onChange={(event) => setForm({ ...form, default_locale: event.target.value })} data-testid="admin-ui-default-locale"><option value="id">Indonesia</option><option value="en">English</option></select></label>{canManage && <button type="button" className="rm-btn-primary inline-flex items-center gap-2" onClick={save} disabled={saving} data-testid="admin-ui-save-button"><Save className="h-4 w-4" /> {saving ? "Menyimpan…" : "Simpan UI"}</button>}</div></header>{error && <div role="alert" className="rounded-md border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200" data-testid="admin-ui-settings-error">{error}</div>}<div className="hidden grid-cols-[32px_1fr_1fr_170px_90px] gap-3 border-b border-white/10 px-3 pb-2 text-[10px] font-bold uppercase tracking-widest text-zinc-600 md:grid"><span /><span>Label Indonesia</span><span>English Label</span><span>Parent / Subtab</span><span>Visibilitas</span></div><DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}><SortableContext items={form.items.map((item) => item.key)} strategy={verticalListSortingStrategy}><div className="border-t border-white/10" data-testid="admin-ui-navigation-builder">{form.items.map((item) => <SortableNavRow key={item.key} item={item} allItems={form.items} onChange={updateItem} readOnly={!canManage} />)}</div></SortableContext></DndContext></div>;
}