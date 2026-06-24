import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { Banknote, AlertCircle, CheckCircle2 } from "lucide-react";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }

const STATUS_PILL = {
  requested: "bg-amber-500/100/15 text-amber-300",
  approved: "bg-sky-500/15 text-sky-300",
  rejected: "bg-red-500/15 text-red-300",
  paid: "bg-emerald-500/15 text-emerald-300",
};

export default function LabelWithdraw() {
  const [window, setWindow] = useState(null);
  const [dash, setDash] = useState(null);
  const [items, setItems] = useState([]);
  const [amount, setAmount] = useState(1_000_000);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [w, d, l] = await Promise.all([
      api.get("/withdraw/window"),
      api.get("/label/dashboard"),
      api.get("/withdraw/label"),
    ]);
    setWindow(w.data);
    setDash(d.data);
    setItems(l.data);
  };
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    setBusy(true);
    try {
      await api.post("/withdraw/label/request", { amount_idr: parseInt(amount, 10) });
      setMsg(`Permintaan withdraw ${fmtIDR(amount)} berhasil diajukan.`);
      setAmount(1_000_000);
      load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  if (!window || !dash) return <div className="text-zinc-500">Memuat…</div>;
  const stats = dash.stats;
  const canRequest = window.request_open && stats.balance_available_idr >= 1_000_000;
  const hasBank = dash.label?.bank_verified || stats.bank_verified;

  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Withdraw</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Tarik Saldo</h1>
        <p className="text-sm text-zinc-400 mt-1">Permintaan withdraw tanggal 1-14, pembayaran 15-20.</p>
      </div>

      <div className={`rounded-2xl p-4 text-sm flex items-start gap-3 ${window.request_open ? "bg-emerald-500/15 text-emerald-300" : window.payment_window ? "bg-sky-500/15 text-sky-300" : "bg-amber-500/100/15 text-amber-300"}`}>
        {window.request_open ? <CheckCircle2 className="w-5 h-5 flex-none" /> : <AlertCircle className="w-5 h-5 flex-none" />}
        <div>
          <div className="font-bold">Tanggal {window.day} {window.month} (Asia/Jakarta)</div>
          <div>{window.message}</div>
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
        <form onSubmit={submit} className="rm-card p-6 space-y-4">
          <h3 className="font-display font-bold text-lg tracking-tight flex items-center gap-2"><Banknote className="w-5 h-5" /> Ajukan Withdraw</h3>
          <div>
            <label className="rm-label">Jumlah (Rp)</label>
            <input
              type="number" min="1000000" max={stats.balance_available_idr} step="50000"
              className="rm-input text-2xl font-display font-bold tracking-tight"
              value={amount} onChange={(e) => setAmount(e.target.value)} data-testid="withdraw-amount-input"
            />
            <div className="flex justify-between text-xs text-zinc-500 mt-1">
              <span>Minimum {fmtIDR(1_000_000)}</span>
              <span>Maks {fmtIDR(stats.balance_available_idr)}</span>
            </div>
          </div>
          {err && <div className="text-sm text-red-600 bg-red-50 rounded-xl px-3 py-2">{err}</div>}
          {msg && <div className="text-sm text-emerald-300 bg-emerald-50 rounded-xl px-3 py-2">{msg}</div>}
          <button className="rm-btn-primary w-full" disabled={busy || !canRequest} data-testid="withdraw-submit-button">
            {!window.request_open ? "Periode permintaan ditutup" : busy ? "Memproses…" : "Ajukan Withdraw"}
          </button>
        </form>
      )}

      <div className="rm-card p-5">
        <h3 className="font-display font-bold text-lg tracking-tight mb-3">Riwayat Withdraw</h3>
        {items.length === 0 ? <div className="text-sm text-zinc-500 py-6 text-center">Belum ada withdraw.</div> : items.map((w) => (
          <div key={w.id} className="py-3 border-b border-white/5 last:border-0 flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="font-display font-bold text-lg tracking-tight">{fmtIDR(w.amount_idr)}</div>
              <div className="text-xs text-zinc-500">Request {w.request_date?.slice(0, 10)} {w.paid_date && `• Dibayar ${w.paid_date.slice(0, 10)}`}</div>
              {w.admin_note && <div className="text-xs text-amber-300 mt-1">Catatan: {w.admin_note}</div>}
            </div>
            <span className={`px-2.5 py-1 rounded-full text-xs font-bold capitalize ${STATUS_PILL[w.status] || "bg-white/[0.06] text-zinc-400"}`}>{w.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
function Card({ label, v, accent }) {
  const cls = { emerald: "text-emerald-300", amber: "text-amber-300", sky: "text-sky-300" }[accent] || "";
  return <div className="rm-card p-4"><div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">{label}</div><div className={`font-display text-xl md:text-2xl font-extrabold tracking-tighter mt-1 ${cls}`}>{v}</div></div>;
}
