import React, { useCallback, useEffect, useState } from "react";
import { Plus, X } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { openXenditCheckout } from "@/api/payments";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const idr = (value) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value || 0);
const day = (value) => (value ? new Date(`${value}T00:00:00+07:00`).toLocaleDateString("id-ID", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Jakarta" }) : "—");
export const TOKEN_EVENT = "rilismusik:tokens-changed";
const KIND = { purchase: "Pembelian", release_reserve: "Dipakai rilisan", release_refund: "Dikembalikan", admin_adjust: "Penyesuaian admin" };

export function useTokenWallet() {
  const { user } = useAuth();
  const [wallet, setWallet] = useState(null);
  const load = useCallback(() => api.get("/tokens/me").then(({ data }) => setWallet(data)).catch(() => setWallet(null)), []);
  useEffect(() => {
    load();
    window.addEventListener(TOKEN_EVENT, load);
    return () => window.removeEventListener(TOKEN_EVENT, load);
  }, [load, user?.id, user?.active_label_id]);
  return { wallet, reload: load };
}

// Buying tokens: flat price per token via the existing Xendit checkout.
export function TokenDialog({ wallet, onClose }) {
  const { t } = useAppPreferences();
  const [quantity, setQuantity] = useState(5);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const price = wallet?.token_price_idr || 35000;
  const max = wallet?.max_purchase || 500;
  const valid = Number.isInteger(quantity) && quantity >= 1 && quantity <= max;
  const buy = async () => {
    setBusy(true); setError("");
    try {
      const { data } = await api.post("/tokens/purchase", { quantity });
      await openXenditCheckout(data.id);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail || requestError.message));
      setBusy(false);
    }
  };
  return <div className="v13-dialog" role="dialog" aria-modal="true" aria-label={t("Beli token")} data-testid="token-dialog">
    <button type="button" className="v13-dialog-backdrop" aria-label={t("Tutup")} onClick={onClose} />
    <div className="v13-dialog-panel" style={{ width: "min(520px, 100%)" }}>
      <div className="flex items-start justify-between gap-4"><div><h2 className="text-2xl font-medium tracking-tight">{t("Token")}</h2><p className="mt-1 text-sm text-[var(--ui-muted)]">{t("Saldo")} <strong className="text-[var(--ui-text)]">{wallet?.balance ?? 0} {t("token")}</strong> · 1 {t("token")} = {idr(price)}</p></div><button type="button" className="v13-chevron" onClick={onClose} aria-label={t("Tutup")}><X /></button></div>
      <p className="mt-4 text-sm text-[var(--ui-muted)]">{t("Token dipakai untuk mode rilis Express dan MAX. Token tidak kedaluwarsa, tidak dapat ditarik, dan pembelian token tidak dapat dikembalikan.")}</p>
      <div className="mt-5 grid grid-cols-4 gap-2">{[1, 5, 10, 25].map((value) => <button key={value} type="button" onClick={() => setQuantity(value)} className={`rounded-xl py-3 text-sm ${quantity === value ? "bg-[var(--ui-text)] text-[var(--ui-surface)]" : "bg-[var(--ui-surface)]"}`}>{value}</button>)}</div>
      <label className="mt-3 block text-sm">{t("Jumlah lain")}<input type="number" min={1} max={max} value={quantity} onChange={(event) => setQuantity(Math.floor(Number(event.target.value)))} className="v13-select mt-1 w-full" data-testid="token-quantity" /></label>
      <div className="mt-5 flex items-center justify-between text-sm"><span className="text-[var(--ui-muted)]">{t("Total")}</span><strong className="text-xl font-normal">{valid ? idr(quantity * price) : "—"}</strong></div>
      {error && <p role="alert" className="mt-3 text-sm text-[var(--v13-urgent)]">{error}</p>}
      <button type="button" className="v13-plan-cta mt-5" disabled={!valid || busy} onClick={buy} data-testid="token-buy">{busy ? t("Membuka Xendit…") : t("Bayar via Xendit")}</button>
    </div>
  </div>;
}

export function TokenChip() {
  const { t } = useAppPreferences();
  const { wallet } = useTokenWallet();
  const [open, setOpen] = useState(false);
  if (!wallet) return null;
  return <>
    <button type="button" className="v13-plan-chip" onClick={() => setOpen(true)} title={t("Beli token")} data-testid="token-chip"><span className="v13-coin" aria-hidden="true">R</span><span className="tabular-nums">{wallet.balance} {t("token")}</span><Plus className="h-3.5 w-3.5" /></button>
    {open && <TokenDialog wallet={wallet} onClose={() => setOpen(false)} />}
  </>;
}

export function TokenHistory() {
  const { t } = useAppPreferences();
  const { wallet } = useTokenWallet();
  const [open, setOpen] = useState(false);
  if (!wallet) return null;
  return <section className="v13-card" data-testid="token-history">
    <div className="v13-card-head"><div><h2>{t("Token")}</h2><p className="mt-1 text-sm text-[var(--ui-muted)]">{t("Saldo")} {wallet.balance} {t("token")} · 1 {t("token")} = {idr(wallet.token_price_idr)}</p></div><button type="button" className="v13-plan-cta shrink-0 px-5" style={{ width: "auto" }} onClick={() => setOpen(true)} data-testid="token-history-buy">{t("Beli token")}</button></div>
    <div className="v13-card-body">{wallet.ledger.length === 0 ? <p className="py-4 text-sm text-[var(--ui-muted)]">{t("Belum ada riwayat token.")}</p> : wallet.ledger.map((entry) => <div key={entry.id} className="v13-row"><div className="min-w-0"><div className="v13-row-title">{t(KIND[entry.kind] || entry.kind)}</div><div className="v13-row-sub truncate">{entry.note || "—"} · {new Date(entry.created_at).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })}</div></div><strong className={`shrink-0 font-normal tabular-nums ${entry.tokens > 0 ? "text-[var(--v13-up)]" : ""}`}>{entry.tokens > 0 ? "+" : ""}{entry.tokens}</strong></div>)}</div>
    {open && <TokenDialog wallet={wallet} onClose={() => setOpen(false)} />}
  </section>;
}

// Standard / Express / MAX picker for the release submission step.
export function ReleaseModePicker({ trackCount, releaseDate, mode, onMode, packageName }) {
  const { t } = useAppPreferences();
  const [data, setData] = useState(null);
  const [buying, setBuying] = useState(false);
  const { wallet } = useTokenWallet();
  useEffect(() => {
    let active = true;
    api.get("/tokens/release-modes", { params: { tracks: Math.max(1, trackCount || 1) } }).then((response) => { if (active) setData(response.data); }).catch(() => { if (active) setData(null); });
    return () => { active = false; };
  }, [trackCount, wallet?.balance]);
  if (!data) return null;
  const selected = data.modes.find((item) => item.id === mode) || data.modes[0];
  const tooEarly = releaseDate && selected.earliest_date && releaseDate < selected.earliest_date;
  const short = selected.tokens > data.balance;
  return <section className="v13-card" data-testid="release-mode-picker">
    <div className="v13-card-head"><div><h2>{t("Mode rilis")}</h2><p className="mt-1 text-sm text-[var(--ui-muted)]">{t("Hari kerja dihitung Senin–Jumat WIB. Hari libur belum diperhitungkan; tanggal tercepat bukan jaminan tayang.")}</p></div><span className="shrink-0 text-sm text-[var(--ui-muted)]">{t("Saldo")} {data.balance} {t("token")}</span></div>
    <div className="v13-card-body grid gap-3 md:grid-cols-3">
      {data.modes.map((item) => <button key={item.id} type="button" disabled={!item.available} onClick={() => onMode(item.id)} aria-pressed={mode === item.id} className={`rounded-2xl border p-4 text-left transition-colors disabled:opacity-40 ${mode === item.id ? "border-[var(--ui-text)] bg-[var(--ui-raised)]" : "border-[var(--ui-border)] hover:bg-[var(--ui-hover)]"}`} data-testid={`release-mode-${item.id}`}>
        <div className="flex items-center justify-between"><strong className="text-base font-semibold">{item.name}</strong><span className="v13-pill" data-tone={item.id === "max" ? "mustard" : item.id === "express" ? "blue" : undefined}>{item.id === "standard" ? t("Ikut paket") : `${item.tokens} ${t("token")}`}</span></div>
        <div className="mt-3 text-sm">{item.available ? `${t("Paling cepat")} ${day(item.earliest_date)}` : t("Tidak tersedia Jumat setelah 12.00 WIB")}</div>
        <div className="mt-1 text-xs text-[var(--ui-muted)]">{item.id === "standard" ? `${item.lead_working_days} ${t("hari kerja")} · ${packageName === "Basic" ? t("bayar per lagu") : t("tanpa biaya per lagu")}` : `${item.lead_working_days} ${t("hari kerja")} · ${item.tokens_per_track} ${t("token per lagu")}`}</div>
      </button>)}
    </div>
    {(tooEarly || (mode !== "standard" && short)) && <div className="v13-card-body pt-0">
      {tooEarly && <p role="alert" className="text-sm text-[var(--v13-urgent)]">{t("Tanggal rilis lebih awal dari batas mode ini. Ubah tanggal atau pilih mode yang lebih cepat.")}</p>}
      {mode !== "standard" && short && <p role="alert" className="text-sm text-[var(--v13-urgent)]">{t("Saldo token kurang")} {selected.tokens - data.balance} {t("token")}. <button type="button" className="underline" onClick={() => setBuying(true)}>{t("Beli token")}</button></p>}
    </div>}
    {buying && <TokenDialog wallet={wallet} onClose={() => setBuying(false)} />}
  </section>;
}


// Express/MAX marker shown next to a release status.
export function ReleaseModeTag({ release }) {
  const { t } = useAppPreferences();
  const mode = release?.service_mode;
  if (!mode || mode === "standard") return null;
  const state = { reserved: "dicadangkan", settled: "terpakai", refunded: "dikembalikan" }[release.token_status];
  return <span className="v13-pill" data-tone={mode === "max" ? "mustard" : "blue"} data-testid="release-mode-tag">{mode === "max" ? "MAX" : "Express"}{release.token_reserved ? ` · ${release.token_reserved} ${t("token")}${state ? ` ${t(state)}` : ""}` : ""}</span>;
}
