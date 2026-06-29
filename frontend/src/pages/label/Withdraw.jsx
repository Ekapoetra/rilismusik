import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { Banknote, AlertCircle, CheckCircle2, Calendar, Layers } from "lucide-react";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
function fmtPeriod(p) {
  if (!p || p.length !== 7) return p || "—";
  const [y, m] = p.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
  return `${months[parseInt(m, 10) - 1] || m} ${y}`;
}

const STATUS_PILL = {
  requested: "bg-amber-500/15 text-amber-300",
  approved: "bg-sky-500/15 text-sky-300",
  rejected: "bg-red-500/15 text-red-300",
  paid: "bg-emerald-500/15 text-emerald-300",
};

export default function LabelWithdraw() {
  const [windowState, setWindowState] = useState(null);
  const [dash, setDash] = useState(null);
  const [computed, setComputed] = useState(null);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [w, d, c, l] = await Promise.all([
      api.get("/withdraw/window"),
      api.get("/label/dashboard"),
      api.get("/withdraw/label/computed"),
      api.get("/withdraw/label"),
    ]);
    setWindowState(w.data);
    setDash(d.data);
    setComputed(c.data);
    setItems(l.data);
  };
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    if (!computed?.can_withdraw) return;
    if (!window.confirm(
      `Anda akan menarik SELURUH royalti dari ${fmtPeriod(computed.period_from)} sampai ${fmtPeriod(computed.period_to)} sejumlah ${fmtIDR(computed.withdrawable_idr)}. Lanjutkan?`
    )) return;
    setBusy(true);
    try {
      const { data } = await api.post("/withdraw/label/request");
      setMsg(`Permintaan withdraw ${fmtIDR(data.amount_idr)} (periode ${fmtPeriod(data.period_from)} - ${fmtPeriod(data.period_to)}) berhasil diajukan.`);
      load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  if (!windowState || !dash || !computed) return <div className="text-zinc-500">Memuat…</div>;
  const stats = dash.stats;
  const canRequest = windowState.request_open && computed.can_withdraw;
  const hasBank = dash.label?.bank_verified || stats.bank_verified;

  return (
    <div className="space-y-5 max-w-3xl" data-testid="label-withdraw-page">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Withdraw</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Tarik Saldo</h1>
        <p className="text-sm text-zinc-400 mt-1">Permintaan withdraw tanggal 1-14, pembayaran 15-20. Setiap withdraw otomatis menarik <b>semua royalti</b> dari periode setelah withdraw terakhir hingga bulan laporan terbaru — tidak bisa parsial.</p>
      </div>

      <div className={`rounded-2xl p-4 text-sm flex items-start gap-3 ${windowState.request_open ? "bg-emerald-500/15 text-emerald-300" : windowState.payment_window ? "bg-sky-500/15 text-sky-300" : "bg-amber-500/15 text-amber-300"}`}>
        {windowState.request_open ? <CheckCircle2 className="w-5 h-5 flex-none" /> : <AlertCircle className="w-5 h-5 flex-none" />}
        <div>
          <div className="font-bold">Tanggal {windowState.day} {windowState.month} (Asia/Jakarta)</div>
          <div>{windowState.message}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card label="Saldo Tersedia" v={fmtIDR(stats.balance_available_idr)} accent="emerald" />
        <Card label="Saldo Pending" v={fmtIDR(stats.balance_pending_idr)} accent="amber" />
        <Card label="Withdraw Diproses" v={fmtIDR(stats.balance_withdraw_requested_idr)} accent="sky" />
      </div>

      {!hasBank ? (
        <div className="rm-card p-6 text-center">
          <AlertCircle className="w-10 h-10 mx-auto text-amber-400 mb-3" />
          <div className="font-display font-bold text-lg">Rekening belum terverifikasi</div>
          <p className="text-sm text-zinc-400 mt-1">Hubungi admin untuk verifikasi atau input rekening dulu.</p>
          <Link to="/label/profile" className="rm-btn-primary inline-block mt-4" data-testid="withdraw-go-profile">Input Rekening</Link>
        </div>
      ) : (
        <form onSubmit={submit} className="rm-card p-6 space-y-5" data-testid="withdraw-fifo-form">
          <h3 className="font-display font-bold text-lg tracking-tight flex items-center gap-2"><Banknote className="w-5 h-5" /> Ajukan Withdraw FIFO</h3>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-zinc-500 font-bold">
                <Calendar className="w-3.5 h-3.5" /> Range Bulan Laporan yang Akan Ditarik
              </div>
              {computed.last_withdrawn_period && (
                <span className="text-[10px] text-zinc-500">Withdraw terakhir: {fmtPeriod(computed.last_withdrawn_period)}</span>
              )}
            </div>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <div className="font-display font-extrabold text-lg tracking-tight text-white">
                  {computed.period_from ? (
                    <>{fmtPeriod(computed.period_from)} <span className="text-zinc-500 mx-1">→</span> {fmtPeriod(computed.period_to)}</>
                  ) : (
                    <span className="text-zinc-500">Tidak ada periode tersedia</span>
                  )}
                </div>
                <div className="text-xs text-zinc-400 mt-1 flex items-center gap-3">
                  <span className="inline-flex items-center gap-1"><Layers className="w-3 h-3" /> {computed.lines_count.toLocaleString("id-ID")} baris royalti</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-[11px] uppercase tracking-widest text-zinc-500 font-bold">Total Withdraw</div>
                <div className="font-display text-2xl md:text-3xl font-extrabold tracking-tighter bg-gradient-to-r from-emerald-300 to-emerald-500 bg-clip-text text-transparent" data-testid="withdraw-fifo-amount">
                  {fmtIDR(computed.withdrawable_idr)}
                </div>
              </div>
            </div>
            {!computed.can_withdraw && computed.reason && (
              <div className="text-xs text-amber-300 bg-amber-500/10 rounded-xl px-3 py-2 mt-2 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 flex-none mt-0.5" /> {computed.reason}
              </div>
            )}
          </div>

          {err && <div className="text-sm text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-xl px-3 py-2" data-testid="withdraw-error">{err}</div>}
          {msg && <div className="text-sm text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-3 py-2" data-testid="withdraw-success">{msg}</div>}

          <button
            className="rm-btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={busy || !canRequest}
            data-testid="withdraw-submit-button"
          >
            {!windowState.request_open
              ? "Periode permintaan ditutup"
              : !computed.can_withdraw
                ? "Belum bisa withdraw"
                : busy
                  ? "Memproses…"
                  : `Tarik Semua: ${fmtIDR(computed.withdrawable_idr)}`}
          </button>
        </form>
      )}

      <div className="rm-card p-5">
        <h3 className="font-display font-bold text-lg tracking-tight mb-3">Riwayat Withdraw</h3>
        {items.length === 0 ? (
          <div className="text-sm text-zinc-500 py-6 text-center">Belum ada withdraw.</div>
        ) : (
          <div className="space-y-1">
            {items.map((w) => (
              <div key={w.id} className="py-3 border-b border-white/5 last:border-0 flex items-center justify-between flex-wrap gap-3" data-testid={`withdraw-history-${w.id}`}>
                <div>
                  <div className="font-display font-bold text-lg tracking-tight">{fmtIDR(w.amount_idr)}</div>
                  <div className="text-xs text-zinc-500">
                    Request {w.request_date?.slice(0, 10)}
                    {w.paid_date && ` • Dibayar ${w.paid_date.slice(0, 10)}`}
                    {(w.period_from || w.period_to) && (
                      <span className="ml-2 inline-flex items-center gap-1 text-zinc-400">
                        <Calendar className="w-3 h-3" /> {fmtPeriod(w.period_from)} - {fmtPeriod(w.period_to)}
                      </span>
                    )}
                  </div>
                  {w.admin_note && <div className="text-xs text-amber-300 mt-1">Catatan: {w.admin_note}</div>}
                </div>
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold capitalize ${STATUS_PILL[w.status] || "bg-white/[0.06] text-zinc-400"}`}>{w.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Card({ label, v, accent }) {
  const cls = { emerald: "text-emerald-300", amber: "text-amber-300", sky: "text-sky-300" }[accent] || "";
  return (
    <div className="rm-card p-4">
      <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">{label}</div>
      <div className={`font-display text-xl md:text-2xl font-extrabold tracking-tighter mt-1 ${cls}`}>{v}</div>
    </div>
  );
}
