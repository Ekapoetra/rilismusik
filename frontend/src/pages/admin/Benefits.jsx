import { useCallback, useEffect, useMemo, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { fmtDateTimeWib } from "@/utils/format";
import Notice from "@/components/shared/Notice";
import PageHeader from "@/components/shared/PageHeader";
import { toast } from "@/components/ui/sonner";
import { Gift, RefreshCw, Plus, Sparkles, X, Search } from "lucide-react";

const PACKAGE_LABELS = {
  pay_per_release: "Basic", annual_normal: "Studio", annual_vip: "Pro", multi_label: "Business",
};
const SERVICE_OPTIONS = [{ value: "any", label: "Semua layanan gratis" }, { value: "wami", label: "Registrasi WAMI" }];

export default function AdminBenefits() {
  const [monitor, setMonitor] = useState(null);
  const [grants, setGrants] = useState([]);
  const [products, setProducts] = useState([]);
  const [labels, setLabels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [editor, setEditor] = useState(null); // {label_id, label_name, service, quantity, days, note}
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    try {
      const [m, g, p] = await Promise.all([
        api.get("/admin/benefits/monitor"),
        api.get("/admin/benefits/grants", { params: { active: !showHistory } }),
        api.get("/payments/admin/products").catch(() => ({ data: [] })),
      ]);
      setMonitor(m.data); setGrants(g.data.items || []); setProducts(p.data.items || p.data || []);
    } catch (e) { setErr(formatApiError(e)); }
    finally { setLoading(false); }
  }, [showHistory]);

  useEffect(() => { load(); }, [load]);

  const findLabel = async (q) => {
    const { data } = await api.get("/admin/labels", { params: { q } });
    return data.items || data || [];
  };

  const openEditor = async (preset) => {
    setEditor({ label_id: preset?.label_id || "", label_name: preset?.label_name || "",
      service: "any", quantity: 1, days: 30, note: "" });
    if (!labels.length) { try { setLabels(await findLabel("")); } catch (e) { /* optional */ } }
  };

  const save = async () => {
    if (!editor.label_id) { toast.error("Pilih label"); return; }
    if (!editor.note.trim() || editor.note.trim().length < 3) { toast.error("Tuliskan alasan bonus"); return; }
    setSaving(true);
    try {
      await api.post("/admin/benefits/grant", {
        label_id: editor.label_id, service: editor.service,
        quantity: Number(editor.quantity), days: Number(editor.days), note: editor.note.trim(),
      });
      toast.success("Bonus diberikan");
      setEditor(null); load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSaving(false); }
  };

  const revoke = async (id) => {
    if (!window.confirm("Cabut bonus ini? Sisa kuota bonus akan hangus.")) return;
    try { await api.post(`/admin/benefits/grants/${id}/revoke`); toast.success("Bonus dicabut"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const serviceOptions = useMemo(() => [
    ...SERVICE_OPTIONS,
    ...products.map((p) => ({ value: p.id, label: p.name || p.id })),
  ], [products]);

  const serviceLabel = (v) => serviceOptions.find((o) => o.value === v)?.label || v;
  const filteredLabels = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return labels;
    return labels.filter((l) => (l.label_name || "").toLowerCase().includes(q));
  }, [labels, search]);

  return (
    <div className="space-y-6" data-testid="admin-benefits-page">
      <PageHeader bordered eyebrow="Layanan" title="Benefit & Bonus" icon={Gift}
        sub="Monitor label yang layak mendapat bonus, lalu berikan layanan gratis terjadwal — WAMI, add-on spesifik, atau bebas pilih.">
        <div className="flex gap-2">
          <button type="button" onClick={load} className="rm-btn-ghost inline-flex items-center gap-2 text-sm" data-testid="benefits-refresh"><RefreshCw className="h-4 w-4" /> Muat ulang</button>
          <button type="button" onClick={() => openEditor(null)} className="rm-btn-primary inline-flex items-center gap-2 text-sm" data-testid="benefits-grant-new"><Plus className="h-4 w-4" /> Beri Bonus</button>
        </div>
      </PageHeader>

      {err && <Notice kind="error" testId="benefits-error">{err}</Notice>}

      <section className="rm-card p-5 space-y-3" data-testid="benefits-monitor">
        <h2 className="font-display text-lg font-bold flex items-center gap-2"><Sparkles className="h-5 w-5 text-pink-400" /> Rekomendasi Penerima Bonus</h2>
        <p className="text-sm text-zinc-400">Label dengan kondisi yang mendekati layak diberi bonus — beserta alasannya.</p>
        {loading ? <div className="text-sm text-zinc-500">Memuat…</div> :
         (monitor?.items || []).length === 0 ? <div className="text-sm text-zinc-500">Belum ada kandidat bulan ini.</div> : (
          <div className="space-y-2">
            {monitor.items.map((item) => (
              <div key={item.label_id} className="rm-glass rounded-2xl p-4 flex flex-wrap items-start justify-between gap-3" data-testid={`benefit-candidate-${item.label_id}`}>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 font-bold">{item.label_name}
                    <span className="rm-badge">{PACKAGE_LABELS[item.package] || item.package}</span></div>
                  <ul className="text-xs text-zinc-400 space-y-1">
                    {item.signals.map((s) => <li key={s.key}><span className="text-pink-300 font-semibold">{(monitor.signal_keys || {})[s.key] || s.key}:</span> {s.text}</li>)}
                  </ul>
                </div>
                <button className="rm-btn-ghost text-sm" onClick={() => openEditor(item)} data-testid={`benefit-grant-${item.label_id}`}>Beri Bonus</button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rm-card p-5 space-y-3" data-testid="benefits-active">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="font-display text-lg font-bold">{showHistory ? "Riwayat Bonus" : "Bonus Aktif"}</h2>
          <button type="button" className="rm-btn-ghost text-xs" onClick={() => setShowHistory((v) => !v)}
            data-testid="benefits-history-toggle">
            {showHistory ? "Lihat yang aktif" : "Lihat riwayat"}
          </button>
        </div>
        {grants.length === 0 ? <div className="text-sm text-zinc-500">{showHistory ? "Belum ada riwayat bonus." : "Belum ada bonus aktif."}</div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase tracking-widest text-zinc-500">
                <th className="py-2 pr-4">Label</th><th className="py-2 pr-4">Layanan</th>
                <th className="py-2 pr-4">Terpakai</th><th className="py-2 pr-4">Berlaku s/d</th>
                <th className="py-2 pr-4">Catatan</th><th className="py-2" /></tr></thead>
              <tbody>
                {grants.map((g) => {
                  const inactive = g.revoked || new Date(g.expires_at) < new Date();
                  return (
                  <tr key={g.id} className={`border-t border-white/5 ${inactive ? "opacity-50" : ""}`} data-testid={`benefit-grant-row-${g.id}`}>
                    <td className="py-2.5 pr-4 font-semibold">{g.label_name}</td>
                    <td className="py-2.5 pr-4">{serviceLabel(g.service)}</td>
                    <td className="py-2.5 pr-4">{g.used}/{g.quantity}</td>
                    <td className="py-2.5 pr-4">{fmtDateTimeWib(g.expires_at)}{inactive && <span className="ml-2 rm-badge">{g.revoked ? "Dicabut" : "Berakhir"}</span>}</td>
                    <td className="py-2.5 pr-4 text-zinc-400">{g.note}</td>
                    <td className="py-2.5">{!inactive && <button className="rm-btn-ghost text-xs" onClick={() => revoke(g.id)} data-testid={`benefit-revoke-${g.id}`}>Cabut</button>}</td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {editor && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" onClick={() => setEditor(null)} data-testid="benefit-grant-modal">
          <div onClick={(e) => e.stopPropagation()} className="w-full max-w-lg rm-glass-strong rounded-[24px] p-6 space-y-4">
            <div className="flex items-start justify-between">
              <h3 className="font-display font-extrabold text-xl">Beri Bonus</h3>
              <button className="rm-btn-ghost p-1" onClick={() => setEditor(null)}><X className="h-4 w-4" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Label</label>
                {editor.label_id ? (
                  <div className="mt-1 flex items-center gap-2"><span className="font-semibold">{editor.label_name}</span>
                    <button className="text-xs text-zinc-400 underline" onClick={() => setEditor({ ...editor, label_id: "", label_name: "" })}>ganti</button></div>
                ) : (
                  <div className="mt-1 space-y-2">
                    <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                      <input className="rm-input w-full pl-9" placeholder="Cari nama label…" value={search}
                        onChange={(e) => setSearch(e.target.value)} data-testid="benefit-label-search" /></div>
                    <div className="max-h-40 overflow-y-auto space-y-1">
                      {filteredLabels.slice(0, 20).map((l) => (
                        <button key={l.id} type="button" className="w-full text-left rm-glass rounded-lg px-3 py-2 text-sm hover:border-pink-500/40"
                          onClick={() => setEditor({ ...editor, label_id: l.id, label_name: l.label_name })}
                          data-testid={`benefit-pick-${l.id}`}>{l.label_name}</button>
                      ))}
                      {!filteredLabels.length && <div className="text-xs text-zinc-500 px-1">Tidak ada hasil.</div>}
                    </div>
                  </div>
                )}
              </div>
              <div>
                <label className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Layanan</label>
                <select className="rm-input w-full mt-1" value={editor.service} onChange={(e) => setEditor({ ...editor, service: e.target.value })} data-testid="benefit-service">
                  {serviceOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Jumlah</label>
                  <input type="number" min="1" max="100" className="rm-input w-full mt-1" value={editor.quantity}
                    onChange={(e) => setEditor({ ...editor, quantity: e.target.value })} data-testid="benefit-quantity" /></div>
                <div><label className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Berlaku (hari)</label>
                  <input type="number" min="1" max="365" className="rm-input w-full mt-1" value={editor.days}
                    onChange={(e) => setEditor({ ...editor, days: e.target.value })} data-testid="benefit-days" /></div>
              </div>
              <div><label className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Alasan (internal)</label>
                <input className="rm-input w-full mt-1" placeholder="mis. reward rilisan ke-10" value={editor.note}
                  onChange={(e) => setEditor({ ...editor, note: e.target.value })} data-testid="benefit-note" /></div>
            </div>
            <button className="rm-btn-primary w-full" onClick={save} disabled={saving} data-testid="benefit-grant-save">
              {saving ? "Menyimpan…" : "Berikan Bonus"}</button>
          </div>
        </div>
      )}
    </div>
  );
}
