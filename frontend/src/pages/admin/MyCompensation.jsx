import React, { useEffect, useState } from "react";
import { Wallet, Coins, Receipt, History, Download } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { downloadPayslip } from "@/api/payslip";

const fmtIDR = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
const fmtDate = (d) => (d ? new Date(d).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "—");

export default function MyCompensation() {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState("salary");
  useEffect(() => { api.get("/compensation/me").then((r) => setData(r.data)).catch(() => setData({ error: true })); }, []);
  if (!data) return <div className="text-sm text-zinc-500">Memuat…</div>;

  return (
    <div className="space-y-6" data-testid="my-compensation-page">
      <header className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-emerald-500/25 to-sky-500/15"><Wallet className="h-5 w-5 text-emerald-300" /></div>
        <div><h1 className="font-display text-2xl font-extrabold">Kompensasi Saya</h1><p className="text-sm text-zinc-400">Gaji, bonus, dan riwayat payroll Anda.</p></div>
      </header>

      <div className="flex gap-2">
        {[["salary", "Gaji", Wallet], ["bonus", "Bonus", Coins], ["payroll", "Riwayat Payroll", Receipt]].map(([k, label, Icon]) => (
          <button key={k} onClick={() => setTab(k)} className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-semibold ${tab === k ? "bg-white/10 text-white" : "text-zinc-400"}`} data-testid={`comp-tab-${k}`}><Icon className="h-4 w-4" />{label}</button>
        ))}
      </div>

      {tab === "salary" && (
        <div className="space-y-4" data-testid="comp-salary">
          <div className="rm-glass rounded-2xl p-6">
            <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">Gaji Pokok Saat Ini</div>
            <div className="mt-1 font-display text-3xl font-extrabold tabular-nums" data-testid="comp-current-salary">{fmtIDR(data.salary?.salary_idr)}</div>
            {data.salary?.effective_date && <div className="mt-1 text-xs text-zinc-500">Berlaku sejak {fmtDate(data.salary.effective_date)}</div>}
          </div>
          <div className="rm-glass rounded-2xl p-5">
            <div className="mb-3 flex items-center gap-2 text-sm font-bold"><History className="h-4 w-4 text-zinc-400" />Riwayat Gaji</div>
            {(!data.salary_history || !data.salary_history.length) ? <p className="text-sm text-zinc-500">Belum ada riwayat.</p> : (
              <div className="space-y-1.5">
                {data.salary_history.map((h, i) => (
                  <div key={i} className="flex items-center justify-between border-b border-white/5 py-1.5 text-sm last:border-0">
                    <span className="text-zinc-400">Berlaku {fmtDate(h.effective_date)}</span>
                    <span className="tabular-nums">{fmtIDR(h.previous_idr)} → <b>{fmtIDR(h.new_idr)}</b></span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "bonus" && (
        <div className="rm-glass rounded-2xl p-5" data-testid="comp-bonus">
          <div className="flex items-center justify-between"><span className="text-sm font-bold">Total Bonus (dari payroll)</span><span className="font-display text-xl font-extrabold rm-gradient-text">{fmtIDR(data.bonus_total_idr)}</span></div>
          <p className="mt-1 text-xs text-zinc-500">Bonus dihitung sebagai persentase dari total pendapatan perusahaan pada bulan periode payroll.</p>
          {(!data.bonus_history || !data.bonus_history.length) ? <p className="mt-3 text-sm text-zinc-500">Belum ada bonus.</p> : (
            <div className="mt-3 space-y-1.5">
              {data.bonus_history.map((b, i) => (
                <div key={i} className="border-b border-white/5 py-1.5 text-sm last:border-0">
                  <div className="flex items-center justify-between"><span className="text-zinc-300">{b.period_key}</span><span className="tabular-nums font-bold">{fmtIDR(b.bonus_idr)}</span></div>
                  {(b.breakdown || []).length > 0 && <div className="text-xs text-zinc-500">{b.breakdown.map((x) => x.calc_mode === "tiered" ? `${x.scheme_name} (bertingkat)` : `${x.scheme_name} (${x.percent}%)`).join(", ")}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "payroll" && (
        <div className="rm-glass rounded-2xl p-5" data-testid="comp-payroll">
          {(!data.payroll_history || !data.payroll_history.length) ? <p className="text-sm text-zinc-500">Belum ada riwayat payroll.</p> : (
            <div className="space-y-2">
              {data.payroll_history.map((p, i) => (
                <div key={i} className="flex items-center justify-between rounded-xl border border-white/10 px-4 py-2.5 text-sm" data-testid={`payroll-row-${p.period_key || i}`}>
                  <span>{p.period_key || fmtDate(p.calculated_at)}{p.period_status === "finalized" && <span className="ml-2 rounded-full bg-violet-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-violet-300">final</span>}</span>
                  <span className="flex items-center gap-3">
                    <span className="tabular-nums font-bold">{fmtIDR(p.net_payable_idr ?? p.net_payable)}</span>
                    {p.period_status === "finalized" && (
                      <button onClick={() => downloadPayslip(p.payroll_period_id).catch((e) => toast.error(formatApiError(e.response?.data?.detail || e.message)))} className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white transition-colors hover:bg-white/20" data-testid={`payslip-download-${p.period_key}`}><Download className="h-3.5 w-3.5" />Slip</button>
                    )}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
