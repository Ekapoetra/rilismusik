/** Shared display formatters — single source for currency/date presentation. */
export const fmtIDR = (n) =>
  new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);

export const fmtDateTimeWib = (iso, { withYear = true } = {}) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const opts = { timeZone: "Asia/Jakarta", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23" };
  if (withYear) opts.year = "numeric";
  return new Intl.DateTimeFormat("id-ID", opts).format(d).replace(".", ":") + " WIB";
};
