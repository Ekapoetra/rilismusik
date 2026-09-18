import React, { useEffect, useState } from "react";
import { Save, GripVertical, Plus, MoreVertical, ArrowUp, ArrowDown, Trash2, Search } from "lucide-react";
import { DndContext, PointerSensor, TouchSensor, useSensor, useSensors, closestCorners, useDroppable } from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { api, formatApiError } from "@/api/client";
import { useAdminNavigation } from "@/contexts/AdminNavigationContext";
import { toast } from "@/components/ui/sonner";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { AdminSidebarView } from "@/components/shared/AdminLayout";
import SoundSettings from "@/components/shared/SoundSettings";

const newGroupId = () => `grp_${Math.random().toString(36).slice(2, 10)}`;

function MenuRow({ item, groupItems, canManage, onChange }) {
  const { locale } = useAppPreferences();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.key, disabled: !canManage });
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1 };
  const parentOptions = groupItems.filter((m) => m.key !== item.key && !m.parent_key);
  return (
    <div ref={setNodeRef} style={style} className="flex items-center gap-2 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-hover)]/30 px-2 py-1.5" data-testid={`uis-menu-${item.key}`}>
      <button type="button" className="cursor-grab touch-none text-[var(--ui-muted)] active:cursor-grabbing disabled:opacity-30" disabled={!canManage} {...attributes} {...listeners} data-testid={`uis-menu-drag-${item.key}`}><GripVertical className="h-4 w-4" /></button>
      <div className="min-w-0 flex-1">
        <input value={item.labels?.id || ""} disabled={!canManage} onChange={(e) => onChange({ ...item, labels: { ...item.labels, id: e.target.value, en: item.labels?.en || e.target.value } })} style={{ color: "var(--ui-text)", WebkitTextFillColor: "var(--ui-text)" }} className="w-full bg-transparent text-sm font-semibold text-inherit outline-none focus:text-fuchsia-300" data-testid={`uis-menu-name-${item.key}`} />
        <div className="truncate text-[10px] text-[var(--ui-muted)]">{item.labels?.en || item.labels?.id}</div>
      </div>
      <select value={item.parent_key || ""} disabled={!canManage} onChange={(e) => onChange({ ...item, parent_key: e.target.value || null })} className="rm-input h-8 w-32 shrink-0 text-xs" data-testid={`uis-menu-parent-${item.key}`}>
        <option value="">Main Tab</option>
        {parentOptions.map((m) => <option key={m.key} value={m.key}>{m.labels?.[locale] || m.labels?.id}</option>)}
      </select>
    </div>
  );
}

function GroupCard({ group, items, canManage, first, last, onRenameGroup, onMoveGroup, onDeleteGroup, onItemChange }) {
  const { setNodeRef, isOver } = useDroppable({ id: `g:${group.id}`, disabled: !canManage });
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className={`rounded-xl border p-2 transition-colors ${isOver ? "border-fuchsia-400/60 bg-fuchsia-500/5" : "border-[var(--ui-border)]"}`} data-testid={`uis-group-${group.id}`}>
      <div className="mb-2 flex items-center gap-2 px-1">
        <GripVertical className="h-4 w-4 shrink-0 text-[var(--ui-muted)]/50" />
        <div className="min-w-0 flex-1">
          <input value={group.labels?.id || ""} disabled={!canManage} onChange={(e) => onRenameGroup(group.id, e.target.value)} style={{ color: "var(--ui-text)", WebkitTextFillColor: "var(--ui-text)" }} className="w-full bg-transparent text-sm font-bold uppercase tracking-wide text-inherit outline-none focus:text-fuchsia-300" data-testid={`uis-group-name-${group.id}`} />
          <div className="text-[10px] text-[var(--ui-muted)]">{group.labels?.en || group.labels?.id}</div>
        </div>
        <span className="shrink-0 text-[10px] font-semibold text-[var(--ui-muted)]">{items.length} menu</span>
        {canManage && (
          <div className="relative shrink-0">
            <button type="button" onClick={() => setMenuOpen((v) => !v)} className="rounded-md p-1 text-[var(--ui-muted)] hover:bg-[var(--ui-hover)]" data-testid={`uis-group-menu-${group.id}`}><MoreVertical className="h-4 w-4" /></button>
            {menuOpen && (
              <div className="absolute right-0 z-10 mt-1 w-44 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-panel,#1a1a1a)] p-1 text-sm shadow-xl" onMouseLeave={() => setMenuOpen(false)}>
                <button type="button" disabled={first} onClick={() => { onMoveGroup(group.id, -1); setMenuOpen(false); }} className="flex w-full items-center gap-2 rounded px-2 py-1.5 hover:bg-[var(--ui-hover)] disabled:opacity-30" data-testid={`uis-group-up-${group.id}`}><ArrowUp className="h-3.5 w-3.5" />Pindah ke atas</button>
                <button type="button" disabled={last} onClick={() => { onMoveGroup(group.id, 1); setMenuOpen(false); }} className="flex w-full items-center gap-2 rounded px-2 py-1.5 hover:bg-[var(--ui-hover)] disabled:opacity-30" data-testid={`uis-group-down-${group.id}`}><ArrowDown className="h-3.5 w-3.5" />Pindah ke bawah</button>
                <button type="button" onClick={() => { onDeleteGroup(group.id, items.length); setMenuOpen(false); }} className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-red-400 hover:bg-red-500/10" data-testid={`uis-group-delete-${group.id}`}><Trash2 className="h-3.5 w-3.5" />Hapus group kosong</button>
              </div>
            )}
          </div>
        )}
      </div>
      <div ref={setNodeRef} className="min-h-[8px] space-y-1.5">
        <SortableContext items={items.map((m) => m.key)} strategy={verticalListSortingStrategy}>
          {items.map((m) => <MenuRow key={m.key} item={m} groupItems={items} canManage={canManage} onChange={onItemChange} />)}
        </SortableContext>
        {!items.length && <div className="rounded-lg border border-dashed border-[var(--ui-border)] px-3 py-3 text-center text-xs text-[var(--ui-muted)]">Tarik menu ke sini</div>}
      </div>
    </div>
  );
}

export default function UiSettings() {
  const { hasPermission, user, logout } = useAuth();
  const canManage = hasPermission("ui.settings.manage");
  const { reload } = useAdminNavigation();
  const [data, setData] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 8 } }));

  useEffect(() => { api.get("/admin/ui-settings").then(({ data }) => setData(data)).catch((e) => setError(formatApiError(e.response?.data?.detail))); }, []);
  if (!data) return <div className="py-20 text-center text-sm text-zinc-500" data-testid="admin-ui-settings-loading">Memuat pengaturan UI…</div>;

  const groups = [...(data.groups || [])].sort((a, b) => (a.order || 0) - (b.order || 0));
  const itemsOf = (gid) => data.items.filter((it) => it.group_id === gid);

  const updateItem = (next) => setData({ ...data, items: data.items.map((it) => (it.key === next.key ? next : it)) });
  const renameGroup = (gid, name) => setData({ ...data, groups: data.groups.map((g) => (g.id === gid ? { ...g, labels: { id: name, en: g.labels?.en || name } } : g)) });
  const moveGroup = (gid, dir) => {
    const ordered = [...groups];
    const idx = ordered.findIndex((g) => g.id === gid);
    const swap = idx + dir;
    if (swap < 0 || swap >= ordered.length) return;
    [ordered[idx], ordered[swap]] = [ordered[swap], ordered[idx]];
    setData({ ...data, groups: ordered.map((g, i) => ({ ...g, order: i })) });
  };
  const addGroup = () => setData({ ...data, groups: [...data.groups, { id: newGroupId(), labels: { id: "Group Baru", en: "New Group" }, order: data.groups.length }] });
  const deleteGroup = (gid, count) => {
    if (count > 0) { toast.error("Pindahkan menu terlebih dahulu. Group hanya dapat dihapus jika kosong."); return; }
    setData({ ...data, groups: data.groups.filter((g) => g.id !== gid) });
  };

  const onDragEnd = ({ active, over }) => {
    if (!canManage || !over) return;
    const activeKey = active.id;
    const overId = over.id;
    if (activeKey === overId) return;
    const items = [...data.items];
    const ai = items.findIndex((it) => it.key === activeKey);
    if (ai < 0) return;
    let destGroup;
    let insertAt;
    if (typeof overId === "string" && overId.startsWith("g:")) {
      destGroup = overId.slice(2);
      insertAt = items.length;
    } else {
      const oi = items.findIndex((it) => it.key === overId);
      if (oi < 0) return;
      destGroup = items[oi].group_id;
      insertAt = oi;
    }
    const [moved] = items.splice(ai, 1);
    if (moved.group_id !== destGroup && moved.parent_key) moved.parent_key = null;
    moved.group_id = destGroup;
    // any child of the moved item follows it into the new group
    items.forEach((it) => { if (it.parent_key === moved.key) it.group_id = destGroup; });
    const target = insertAt > ai ? insertAt - 1 : insertAt;
    items.splice(Math.max(0, Math.min(target, items.length)), 0, moved);
    setData({ ...data, items });
  };

  const save = async () => {
    setSaving(true); setError("");
    try {
      const orderedItems = [];
      groups.forEach((g) => itemsOf(g.id).forEach((it) => orderedItems.push(it)));
      data.items.forEach((it) => { if (!orderedItems.find((x) => x.key === it.key)) orderedItems.push(it); });
      const payload = {
        default_locale: data.default_locale,
        groups: groups.map((g, i) => ({ id: g.id, labels: { id: g.labels?.id || "", en: g.labels?.en || g.labels?.id || "" }, order: i })),
        items: orderedItems.map((it, index) => ({ key: it.key, route: it.route, labels: it.labels, parent_key: it.parent_key || null, group_id: it.group_id, visible: it.visible !== false, order: index })),
      };
      const { data: saved } = await api.put("/admin/ui-settings", payload);
      setData(saved);
      await reload();
      toast.success("Struktur navigasi tersimpan.");
    } catch (e) { const msg = formatApiError(e.response?.data?.detail); setError(msg); toast.error(msg); } finally { setSaving(false); }
  };

  const query = q.trim().toLowerCase();

  return (
    <div className="space-y-5" data-testid="admin-ui-settings-page">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">UI Settings</div>
          <h1 className="mt-1 font-display text-3xl font-extrabold">Struktur Navigasi</h1>
          <p className="mt-1 text-sm text-zinc-400">Atur nama group, nama menu, urutan, dan hubungan Parent/Subtab sidebar.</p>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-500">
            <span>✓ English otomatis</span><span>✓ Visibility dari Roles &amp; Permissions</span><span>✓ Group mengikuti posisi menu</span>
          </div>
        </div>
        <div className="flex items-end gap-3">
          <label><span className="rm-label">Bahasa Bawaan</span><select className="rm-input min-w-32" value={data.default_locale} disabled={!canManage} onChange={(e) => setData({ ...data, default_locale: e.target.value })} data-testid="admin-ui-default-locale"><option value="id">Indonesia</option><option value="en">English</option></select></label>
          {canManage && <button type="button" className="rm-btn-primary inline-flex items-center gap-2" onClick={save} disabled={saving} data-testid="admin-ui-save-button"><Save className="h-4 w-4" />{saving ? "Menyimpan…" : "Simpan UI"}</button>}
        </div>
      </header>

      {error && <div role="alert" className="rounded-md border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200" data-testid="admin-ui-settings-error">{error}</div>}

      <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
        <div className="hidden lg:block">
          <div className="sticky top-4">
            <div className="mb-2 text-xs font-bold uppercase tracking-widest text-zinc-500">Live Preview</div>
            <div className="h-[70vh] overflow-hidden rounded-2xl border border-[var(--ui-border)]" data-testid="uis-live-preview">
              <AdminSidebarView instance="preview" collapsed={false} onCollapse={() => {}} items={data.items} groups={groups} user={user} logout={logout} preview />
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="relative flex-1"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari menu atau group…" className="rm-input w-full pl-9" data-testid="uis-search" /></div>
            {canManage && <button type="button" onClick={addGroup} className="rm-btn-ghost inline-flex items-center gap-1.5 whitespace-nowrap" data-testid="uis-add-group"><Plus className="h-4 w-4" />Tambah Group</button>}
          </div>

          <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={onDragEnd}>
            <div className="space-y-2" data-testid="uis-groups">
              {groups.map((g, gi) => {
                let gItems = itemsOf(g.id);
                if (query) {
                  const groupMatch = (g.labels?.id || "").toLowerCase().includes(query);
                  if (!groupMatch) gItems = gItems.filter((m) => (m.labels?.id || "").toLowerCase().includes(query) || (m.labels?.en || "").toLowerCase().includes(query));
                }
                return <GroupCard key={g.id} group={g} items={gItems} canManage={canManage} first={gi === 0} last={gi === groups.length - 1} onRenameGroup={renameGroup} onMoveGroup={moveGroup} onDeleteGroup={deleteGroup} onItemChange={updateItem} />;
              })}
            </div>
          </DndContext>
        </div>
      </div>

      <div className="border-t border-[var(--ui-border)] pt-5"><SoundSettings /></div>
    </div>
  );
}
