import React from "react";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const fmtIDR = (value) => new Intl.NumberFormat("id-ID", {
  style: "currency", currency: "IDR", maximumFractionDigits: 0,
}).format(value || 0);

export const jakartaPeriod = () => {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Asia/Jakarta", year: "numeric", month: "numeric",
  }).formatToParts(new Date());
  return {
    year: Number(parts.find((part) => part.type === "year")?.value),
    month: Number(parts.find((part) => part.type === "month")?.value),
  };
};

export const monthLabel = (month, year) => `${MONTHS[month - 1]} ${year}`;

export const FinancialPeriodOverview = ({
  title, description, year, month, years, onYearChange, onMonthChange,
  metrics, monthly, testIdPrefix,
}) => {
  const maxAmount = Math.max(1, ...monthly.flatMap((row) => metrics.map((metric) => Number(row[metric.key] || 0))));
  return <section className="overflow-hidden rounded-lg border border-white/10 bg-[linear-gradient(135deg,rgba(255,31,142,0.13),rgba(8,7,13,0.96)_50%,rgba(34,197,94,0.08))]" data-testid={`${testIdPrefix}-overview`}>
    <div className="flex flex-col gap-5 p-5 sm:p-7 lg:flex-row lg:items-start lg:justify-between">
      <div><div className="text-xs font-bold uppercase text-zinc-500">Ringkasan Keuangan</div><h2 className="mt-1 font-display text-lg font-bold text-white">{title}</h2><p className="mt-1 text-sm text-zinc-400">{description}</p></div>
      <div className="grid grid-cols-2 gap-2 sm:flex">
        <label className="min-w-32"><span className="rm-label">Bulan</span><select className="rm-input" value={month} onChange={(event) => onMonthChange(Number(event.target.value))} data-testid={`${testIdPrefix}-month-select`}>{MONTHS.map((label, index) => <option value={index + 1} key={label}>{label}</option>)}</select></label>
        <label className="min-w-28"><span className="rm-label">Tahun</span><select className="rm-input" value={year} onChange={(event) => onYearChange(Number(event.target.value))} data-testid={`${testIdPrefix}-year-select`}>{years.map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
      </div>
    </div>
    <div className={`grid border-y border-white/10 ${metrics.length > 1 ? "md:grid-cols-2" : "grid-cols-1"}`}>
      {metrics.map((metric, index) => <div className={`p-5 sm:p-7 ${index ? "border-t border-white/10 md:border-l md:border-t-0" : ""}`} key={metric.key} data-testid={`${testIdPrefix}-${metric.key}-metric`}><div className="text-xs font-bold uppercase text-zinc-500">{metric.label}</div><div className={`mt-2 break-words font-display text-4xl font-extrabold sm:text-5xl ${metric.colorClass}`} data-testid={`${testIdPrefix}-${metric.key}-amount`}>{fmtIDR(metric.amount)}</div><div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-400"><span data-testid={`${testIdPrefix}-${metric.key}-count`}>{Number(metric.count || 0).toLocaleString("id-ID")} transaksi</span><span>Total {year}: <b className="text-zinc-200" data-testid={`${testIdPrefix}-${metric.key}-year-total`}>{fmtIDR(metric.yearAmount)}</b></span></div></div>)}
    </div>
    <div className="p-5 sm:p-7" data-testid={`${testIdPrefix}-monthly-trend`}><div className="mb-3 text-xs font-bold uppercase text-zinc-500">Jejak Bulanan {year}</div><div className="grid grid-cols-6 gap-2 sm:grid-cols-12">{monthly.map((row) => <div className={`flex min-w-0 flex-col items-center gap-2 rounded-md px-1 py-2 ${row.month === month ? "bg-white/10" : "bg-white/[0.025]"}`} key={row.month} data-testid={`${testIdPrefix}-month-${row.month}`}><div className="flex h-16 items-end gap-0.5">{metrics.map((metric) => { const value = Number(row[metric.key] || 0); return <div title={`${metric.label}: ${fmtIDR(value)}`} className={`w-1.5 rounded-t-sm ${metric.barClass}`} style={{ height: value > 0 ? `${Math.max(4, (value / maxAmount) * 100)}%` : "0%" }} key={metric.key} />; })}</div><span className="text-[10px] text-zinc-500">{MONTHS[row.month - 1]}</span></div>)}</div></div>
  </section>;
};