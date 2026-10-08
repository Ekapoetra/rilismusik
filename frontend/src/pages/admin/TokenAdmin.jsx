import React, { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const idr = (value) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value || 0);
const when = (value) => (value ? new Date(value).toLocaleString("id-ID", { timeZone: "Asia/Jakarta", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");
const KIND = { purchase: "Pembelian", release_reserve: "Dipakai rilisan", release_refund: "Dikembalikan", admin_adjust: "Penyesuaian admin" };
const VERDICT = { cheaper: ["green", "Lebih hemat"], equal: [undefined, "Setara · tidak ditawarkan"], more_expensive: ["red", "Lebih mahal · disembunyikan"], not_offered: [undefined, "Tidak ditawarkan"] };

function useData(path) {
  const [state, setState] = useState({ data: null, error: "" });
  const load = useCallback(() => api.get(path).then(({ data }) => setState({ data, error: "" })).catch((error) => setState((current) => ({ ...current, error: formatApiError(error.response?.data?.detail) }))), [path]);
  useEffect(() => { load(); }, [load]);
  return { ...state, reload: load };
}

function Metric({ label, value, note }) {
  return <div className="v13-metric"><h3>{label}</h3><strong>{value}</strong>{note && <div className="mt-auto pt-3 text-xs text-[var(--ui-muted)]">{note}</div>}</div>;
}

function Wallets() {
  const { t } = useAppPreferences();
  const { data, error, reload } = useData("/admin/tokens/wallets");
  const [form, setForm] = useState({ label_id: "", tokens: "", reason: "" });
  const [message, setMessage] = useState(null);
  const [labels, setLabels] = useState([]);
  const [query, setQuery] = useState("");
  useEffect(() => {
    if (query.trim().length < 2) { setLabels([]); return undefined; }
    const timer = setTimeout(() => api.get("/admin/labels", { params: { q: query.trim(), sort_by: "label", sort_dir: "asc" } }).then(({ data: rows }) => setLabels(Array.isArray(rows) ? rows : rows?.items || [])).catch(() => setLabels([])), 300);
    return () => clearTimeout(timer);
  }, [query]);
  const adjust = async (event) => {
    event.preventDefault(); setMessage(null);
    try {
      await api.post("/admin/tokens/adjust", { ...form, tokens: Number(form.tokens) });
      setForm({ label_id: "", tokens: "", reason: "" }); setMessage({ ok: true, text: t("Saldo token diperbarui.") }); reload();
    } catch (requestError) { setMessage({ ok: false, text: formatApiError(requestError.response?.data?.detail) }); }
  };
  if (error && !data) return <p role="alert" className="text-[var(--v13-urgent)]">{error}</p>;
  if (!data) return <p role="status" className="text-[var(--ui-muted)]">{t("Memuat token…")}</p>;
  return <div className="space-y-5" data-testid="token-wallets">
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-3">
      <Metric label={t("Token beredar")} value={`${data.outstanding_tokens} ${t("token")}`} note={`${t("Nilai")} ${idr(data.outstanding_value_idr)} · ${t("pendapatan ditangguhkan")}`} />
      <Metric label={t("Dicadangkan rilisan")} value={`${data.reserved_tokens} ${t("token")}`} note={t("Dikembalikan bila rilisan ditolak")} />
      <Metric label={t("Harga 1 token")} value={idr(data.token_price_idr)} note={t("Diatur di Pengaturan Platform › Paket & Layanan")} />
    </div>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="v13-card overflow-x-auto"><div className="v13-card-head"><h2>{t("Dompet token")}</h2></div><table className="w-full min-w-[560px] text-sm">
        <thead><tr className="text-left text-xs text-[var(--ui-muted)]">{["Akun", "Saldo", "Dicadangkan", "Diperbarui"].map((head) => <th key={head} className="px-5 py-3 font-normal">{t(head)}</th>)}</tr></thead>
        <tbody>{data.wallets.map((wallet) => <tr key={wallet.account_id} className="border-t border-[var(--ui-border)]"><td className="px-5 py-3"><div className="font-medium" translate="no">{wallet.labels[0] || wallet.name || wallet.account_id}</div><div className="text-xs text-[var(--ui-muted)]">{wallet.labels.length > 1 ? `${wallet.labels.length} ${t("label")}` : wallet.name}</div></td><td className="px-5 py-3 tabular-nums">{wallet.balance}</td><td className="px-5 py-3 tabular-nums">{wallet.reserved || "—"}</td><td className="px-5 py-3">{when(wallet.updated_at)}</td></tr>)}</tbody>
      </table>{data.wallets.length === 0 && <p className="px-5 py-8 text-center text-sm text-[var(--ui-muted)]">{t("Belum ada label yang memiliki token.")}</p>}</section>
      <section className="v13-card"><div className="v13-card-head"><h2>{t("Penyesuaian token")}</h2></div>
        <form className="v13-card-body space-y-3" onSubmit={adjust}>
          <label className="block text-sm">{t("Cari label")}<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("Minimal 2 huruf")} className="v13-select mt-1 w-full" /></label>
          <label className="block text-sm">{t("Label")}<select required value={form.label_id} onChange={(event) => setForm({ ...form, label_id: event.target.value })} className="v13-select mt-1 w-full"><option value="">{t("Pilih label")}</option>{labels.map((label) => <option key={label.id} value={label.id}>{label.label_name}</option>)}</select></label>
          <label className="block text-sm">{t("Token (+ tambah / − kurangi)")}<input required type="number" min={-500} max={500} value={form.tokens} onChange={(event) => setForm({ ...form, tokens: event.target.value })} className="v13-select mt-1 w-full" /></label>
          <label className="block text-sm">{t("Alasan")}<textarea required minLength={5} maxLength={500} rows={3} value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} className="mt-1 w-full rounded-[10px] bg-[var(--ui-raised)] p-2 text-sm outline-none" /></label>
          <button type="submit" className="v13-plan-cta">{t("Simpan penyesuaian")}</button>
          {message && <p role={message.ok ? "status" : "alert"} className={`text-sm ${message.ok ? "text-[var(--v13-up)]" : "text-[var(--v13-urgent)]"}`}>{message.text}</p>}
        </form>
      </section>
    </div>
    <section className="v13-card"><div className="v13-card-head"><h2>{t("Riwayat token")}</h2></div><div className="v13-card-body">{data.ledger.length === 0 ? <p className="py-4 text-sm text-[var(--ui-muted)]">{t("Belum ada riwayat.")}</p> : data.ledger.map((entry) => <div key={entry.id} className="v13-row"><div className="min-w-0"><div className="v13-row-title">{t(KIND[entry.kind] || entry.kind)}</div><div className="v13-row-sub truncate">{entry.note || "—"} · {when(entry.created_at)}</div></div><strong className={`font-normal tabular-nums ${entry.tokens > 0 ? "text-[var(--v13-up)]" : ""}`}>{entry.tokens > 0 ? "+" : ""}{entry.tokens}</strong></div>)}</div></section>
  </div>;
}

function Pricing() {
  const { t } = useAppPreferences();
  const { data, error, reload } = useData("/admin/tokens/settings");
  const [form, setForm] = useState(null);
  const [message, setMessage] = useState(null);
  useEffect(() => { if (data) setForm({ token_price_idr: data.token_price_idr, mode_tokens: { ...data.mode_tokens }, lead_working_days: { ...data.lead_working_days } }); }, [data]);
  const save = async (event) => {
    event.preventDefault(); setMessage(null);
    try { await api.put("/admin/tokens/settings", form); setMessage({ ok: true, text: t("Pengaturan tersimpan.") }); reload(); }
    catch (requestError) { setMessage({ ok: false, text: formatApiError(requestError.response?.data?.detail) }); }
  };
  if (error && !data) return <p role="alert" className="text-[var(--v13-urgent)]">{error}</p>;
  if (!data || !form) return <p role="status" className="text-[var(--ui-muted)]">{t("Memuat pengaturan…")}</p>;
  const number = (path, value) => {
    const [group, key] = path.split(".");
    setForm((current) => (key ? { ...current, [group]: { ...current[group], [key]: Number(value) } } : { ...current, [group]: Number(value) }));
  };
  return <div className="grid gap-5 xl:grid-cols-[380px_minmax(0,1fr)]" data-testid="token-pricing">
    <section className="v13-card"><div className="v13-card-head"><h2>{t("Token & mode rilis")}</h2></div>
      <form className="v13-card-body space-y-4" onSubmit={save}>
        <label className="block text-sm">{t("Harga dasar 1 token (Rp)")}<input type="number" min={1000} max={10000000} value={form.token_price_idr} onChange={(event) => number("token_price_idr", event.target.value)} className="v13-select mt-1 w-full" /></label>
        <div className="grid grid-cols-3 gap-2 text-sm"><span className="text-[var(--ui-muted)]">{t("Mode")}</span><span className="text-[var(--ui-muted)]">{t("Token/lagu")}</span><span className="text-[var(--ui-muted)]">{t("Hari kerja")}</span>
          {[["standard", "Standar"], ["express", "Express"], ["max", "MAX"]].map(([mode, name]) => <React.Fragment key={mode}><span className="self-center">{name}</span>{mode === "standard" ? <span className="self-center text-xs text-[var(--ui-muted)]">{t("ikut paket")}</span> : <input type="number" min={1} max={100} value={form.mode_tokens[mode]} onChange={(event) => number(`mode_tokens.${mode}`, event.target.value)} className="v13-select" />}<input type="number" min={1} max={60} value={form.lead_working_days[mode]} onChange={(event) => number(`lead_working_days.${mode}`, event.target.value)} className="v13-select" /></React.Fragment>)}
        </div>
        <p className="text-xs text-[var(--ui-muted)]">{t("Express ≤ MAX untuk token; Standar ≥ Express ≥ MAX untuk hari kerja. MAX hari Jumat sebelum 12.00 WIB dapat tayang Minggu.")}</p>
        <button type="submit" className="v13-plan-cta">{t("Simpan")}</button>
        {message && <p role={message.ok ? "status" : "alert"} className={`text-sm ${message.ok ? "text-[var(--v13-up)]" : "text-[var(--v13-urgent)]"}`}>{message.text}</p>}
      </form>
    </section>
    <section className="v13-card overflow-x-auto"><div className="v13-card-head"><div><h2>{t("Harga layanan")}</h2><p className="mt-1 text-sm text-[var(--ui-muted)]">{t("Token = pembulatan ke atas harga rupiah ÷ harga token. Opsi token hanya ditawarkan bila lebih murah dari rupiah.")}</p></div></div>
      <table className="w-full min-w-[620px] text-sm"><thead><tr className="text-left text-xs text-[var(--ui-muted)]">{["Layanan", "Harga rupiah", "Token", "Biaya token", "Vonis"].map((head) => <th key={head} className="px-5 py-3 font-normal">{t(head)}</th>)}</tr></thead>
        <tbody>{data.services.map((row) => { const [tone, label] = VERDICT[row.verdict] || []; return <tr key={row.code} className="border-t border-[var(--ui-border)]"><td className="px-5 py-3">{t(row.name)}</td><td className="px-5 py-3 tabular-nums">{idr(row.price_idr)}</td><td className="px-5 py-3 tabular-nums">{row.tokens || "—"}</td><td className="px-5 py-3 tabular-nums">{row.tokens ? idr(row.token_cost_idr) : "—"}</td><td className="px-5 py-3"><span className="v13-pill" data-tone={tone}>{t(label)}</span></td></tr>; })}</tbody>
      </table>
    </section>
  </div>;
}

export default function TokenAdmin() {
  const { pathname } = useLocation();
  return pathname.startsWith("/admin/settings") ? <Pricing /> : <Wallets />;
}
