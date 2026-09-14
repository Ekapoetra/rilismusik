// Format a release date value (ISO "YYYY-MM-DD" or date string) as day-month-year
// e.g. "11 September 2026". Falls back to the raw value or an em dash.
const MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];

export const formatReleaseDate = (value) => {
  if (!value) return "—";
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value));
  if (match) {
    const [, year, month, day] = match;
    const label = MONTHS[Number(month) - 1];
    if (label) return `${Number(day)} ${label} ${year}`;
  }
  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) {
    return `${parsed.getDate()} ${MONTHS[parsed.getMonth()]} ${parsed.getFullYear()}`;
  }
  return String(value);
};
