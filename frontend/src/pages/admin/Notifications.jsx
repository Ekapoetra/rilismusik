import React, { useCallback, useEffect, useState } from "react";
import {
  BellRing,
  Check,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Search,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { toast } from "@/components/ui/sonner";

const formatDate = (value) => value
  ? new Date(value).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" })
  : "—";

const typeLabel = (value) => String(value || "umum")
  .replaceAll("_", " ")
  .replace(/\b\w/g, (letter) => letter.toUpperCase());

const FilterField = ({ label, children }) => (
  <label className="min-w-0 max-w-full">
    <span className="rm-label">{label}</span>
    {children}
  </label>
);

const NotificationFilters = ({ values, types, onChange }) => (
  <section
    className="grid w-full min-w-0 max-w-full grid-cols-[minmax(0,1fr)] gap-3 border-y border-white/10 py-5 md:grid-cols-2 xl:grid-cols-[minmax(220px,1fr)_170px_190px_150px_150px]"
    data-testid="admin-notifications-filters"
  >
    <label className="relative min-w-0 max-w-full">
      <span className="rm-label">Pencarian</span>
      <Search className="pointer-events-none absolute bottom-3 left-3 h-4 w-4 text-zinc-600" />
      <input
        className="rm-input min-w-0 max-w-full pl-10"
        value={values.query}
        onChange={(event) => onChange("query", event.target.value)}
        placeholder="Judul, isi, atau jenis…"
        data-testid="admin-notifications-search"
      />
    </label>
    <FilterField label="Status Baca">
      <select
        className="rm-input min-w-0 max-w-full"
        value={values.readStatus}
        onChange={(event) => onChange("readStatus", event.target.value)}
        data-testid="admin-notifications-read-filter"
      >
        <option value="all">Semua</option>
        <option value="unread">Belum Dibaca</option>
        <option value="read">Sudah Dibaca</option>
      </select>
    </FilterField>
    <FilterField label="Jenis">
      <select
        className="rm-input min-w-0 max-w-full"
        value={values.type}
        onChange={(event) => onChange("type", event.target.value)}
        data-testid="admin-notifications-type-filter"
      >
        <option value="">Semua Jenis</option>
        {types.map((item) => <option key={item} value={item}>{typeLabel(item)}</option>)}
      </select>
    </FilterField>
    <FilterField label="Dari Tanggal">
      <input
        type="date"
        className="rm-input min-w-0 max-w-full"
        value={values.dateFrom}
        onChange={(event) => onChange("dateFrom", event.target.value)}
        data-testid="admin-notifications-date-from"
      />
    </FilterField>
    <FilterField label="Sampai Tanggal">
      <input
        type="date"
        className="rm-input min-w-0 max-w-full"
        value={values.dateTo}
        onChange={(event) => onChange("dateTo", event.target.value)}
        data-testid="admin-notifications-date-to"
      />
    </FilterField>
  </section>
);

const NotificationRow = ({ item, showRecipient, onMarkRead, onOpen }) => (
  <article
    className={`grid min-w-0 max-w-full gap-4 overflow-hidden py-5 md:grid-cols-[16px_minmax(0,1fr)_180px_auto] md:items-center ${!item.read_at ? "bg-[#FF1F8E]/[0.025]" : ""}`}
    data-testid={`admin-notification-row-${item.id}`}
  >
    <span
      className={`h-2.5 w-2.5 rounded-full md:mx-auto ${item.read_at ? "bg-zinc-800" : "bg-[#FF1F8E]"}`}
      aria-label={item.read_at ? "Sudah dibaca" : "Belum dibaca"}
      data-testid={`admin-notification-status-${item.id}`}
    />
    <div className="min-w-0 max-w-full">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <h2
          className={`min-w-0 break-words text-sm font-bold ${item.read_at ? "text-zinc-400" : "text-white"}`}
          data-testid={`admin-notification-title-${item.id}`}
        >
          {item.title}
        </h2>
        <span
          className="max-w-full break-words rounded border border-white/10 px-2 py-0.5 text-[10px] font-bold uppercase text-zinc-500"
          data-testid={`admin-notification-type-${item.id}`}
        >
          {typeLabel(item.type)}
        </span>
      </div>
      <p
        className="mt-1 max-w-full break-words text-sm leading-relaxed text-zinc-500"
        data-testid={`admin-notification-body-${item.id}`}
      >
        {item.body}
      </p>
      {showRecipient && (
        <p className="mt-2 max-w-full break-words text-xs text-zinc-600" data-testid={`admin-notification-recipient-${item.id}`}>
          Penerima: {item.recipient?.name || "Admin"} · {item.recipient?.email || "—"}
        </p>
      )}
    </div>
    <time className="text-xs text-zinc-600" dateTime={item.created_at} data-testid={`admin-notification-date-${item.id}`}>
      {formatDate(item.created_at)}
    </time>
    <div className="flex justify-start gap-2 md:justify-end">
      {!item.read_at && item.is_mine && (
        <button
          type="button"
          title="Tandai dibaca"
          onClick={() => onMarkRead(item)}
          className="rounded-md border border-white/10 p-2 text-zinc-400 transition-colors hover:bg-white/5 hover:text-white"
          data-testid={`admin-notification-mark-read-${item.id}`}
        >
          <Check className="h-4 w-4" />
        </button>
      )}
      {item.link?.startsWith("/") && (
        <button
          type="button"
          title="Buka tujuan"
          onClick={() => onOpen(item)}
          className="rounded-md border border-white/10 p-2 text-zinc-400 transition-colors hover:bg-white/5 hover:text-white"
          data-testid={`admin-notification-open-${item.id}`}
        >
          <ExternalLink className="h-4 w-4" />
        </button>
      )}
    </div>
  </article>
);

const NotificationPagination = ({ page, pages, onPageChange }) => (
  <footer className="grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
    <span
      className="col-span-2 text-center text-xs text-zinc-500 sm:col-span-1 sm:col-start-2 sm:row-start-1"
      data-testid="admin-notifications-page-indicator"
    >
      Halaman {page} dari {pages}
    </span>
    <button
      type="button"
      className="rm-btn-ghost inline-flex min-w-0 items-center justify-center gap-2 sm:col-start-1 sm:row-start-1 sm:justify-self-start"
      disabled={page <= 1}
      onClick={() => onPageChange(page - 1)}
      data-testid="admin-notifications-prev"
    >
      <ChevronLeft className="h-4 w-4 shrink-0" /> Sebelumnya
    </button>
    <button
      type="button"
      className="rm-btn-ghost inline-flex min-w-0 items-center justify-center gap-2 sm:col-start-3 sm:row-start-1 sm:justify-self-end"
      disabled={page >= pages}
      onClick={() => onPageChange(page + 1)}
      data-testid="admin-notifications-next"
    >
      Berikutnya <ChevronRight className="h-4 w-4 shrink-0" />
    </button>
  </footer>
);

export default function AdminNotifications() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isSuper = user?.role === "super_admin";
  const [scope, setScope] = useState("mine");
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [readStatus, setReadStatus] = useState("all");
  const [type, setType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0, pages: 1, unread_count: 0, types: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => { setSearch(query.trim()); setPage(1); }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/notifications/admin/log", {
        params: {
          scope,
          page,
          limit: 25,
          read_status: readStatus,
          q: search || undefined,
          ntype: type || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        },
      });
      setData(response.data);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, [scope, page, readStatus, search, type, dateFrom, dateTo]);

  useEffect(() => { load(); }, [load]);

  const updateFilter = (field, value) => {
    if (field === "query") setQuery(value);
    if (field === "readStatus") setReadStatus(value);
    if (field === "type") setType(value);
    if (field === "dateFrom") setDateFrom(value);
    if (field === "dateTo") setDateTo(value);
    if (field !== "query") setPage(1);
  };

  const notifyUpdated = () => window.dispatchEvent(new CustomEvent("rilismusik:notifications-updated"));

  const markRead = async (item, followLink = false) => {
    try {
      if (!item.read_at && item.is_mine) {
        await api.post(`/notifications/mark-read/${item.id}`);
        notifyUpdated();
        await load();
      }
      if (followLink && item.link?.startsWith("/")) navigate(item.link);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail));
    }
  };

  const markAll = async () => {
    try {
      await api.post("/notifications/mark-all-read");
      notifyUpdated();
      await load();
      toast.success("Semua notifikasi Anda ditandai sudah dibaca.");
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail));
    }
  };

  const changeScope = (next) => { setScope(next); setPage(1); };
  const pages = data.pages || 1;

  return (
    <div className="w-full min-w-0 max-w-full space-y-7 overflow-x-hidden" data-testid="admin-notifications-page">
      <header className="flex min-w-0 flex-col items-stretch gap-4 border-b border-white/10 pb-6 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
        <div className="min-w-0">
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Pusat Notifikasi</div>
          <h1 className="mt-1 break-words font-display text-4xl font-extrabold">Riwayat Notifikasi</h1>
          <p className="mt-2 max-w-full text-sm text-zinc-400">Periksa kembali seluruh notifikasi in-app agar tidak ada tindak lanjut yang terlewat.</p>
        </div>
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3 sm:justify-end">
          <div className="text-left sm:text-right">
            <div className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">Belum Dibaca</div>
            <div className="font-mono text-2xl font-bold text-[#FF4FA8]" data-testid="admin-notifications-unread-count">{data.unread_count}</div>
          </div>
          <button
            type="button"
            className="rm-btn-ghost inline-flex min-w-0 items-center justify-center gap-2"
            onClick={markAll}
            disabled={data.unread_count === 0}
            data-testid="admin-notifications-mark-all"
          >
            <CheckCheck className="h-4 w-4 shrink-0" /> Tandai Semua Dibaca
          </button>
        </div>
      </header>

      {isSuper && (
        <div className="flex w-full min-w-0 max-w-full rounded-md border border-white/10 bg-white/[0.03] p-1 sm:inline-flex sm:w-auto" data-testid="admin-notifications-scope-tabs">
          <button type="button" onClick={() => changeScope("mine")} className={`min-w-0 flex-1 rounded px-3 py-2 text-sm font-bold transition-colors sm:flex-none sm:px-4 ${scope === "mine" ? "bg-white text-black" : "text-zinc-500 hover:text-white"}`} data-testid="admin-notifications-scope-mine">Milik Saya</button>
          <button type="button" onClick={() => changeScope("all")} className={`min-w-0 flex-1 rounded px-3 py-2 text-sm font-bold transition-colors sm:flex-none sm:px-4 ${scope === "all" ? "bg-white text-black" : "text-zinc-500 hover:text-white"}`} data-testid="admin-notifications-scope-all">Semua Admin</button>
        </div>
      )}

      <NotificationFilters
        values={{ query, readStatus, type, dateFrom, dateTo }}
        types={data.types}
        onChange={updateFilter}
      />

      {error && <div role="alert" className="rounded-md border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200" data-testid="admin-notifications-error">{error}</div>}

      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2 text-xs text-zinc-500">
        <span data-testid="admin-notifications-total">{data.total} notifikasi ditemukan</span>
        {scope === "all" && <span data-testid="admin-notifications-audit-mode">Mode audit Super Admin · baca-saja untuk penerima lain</span>}
      </div>

      <section className="min-w-0 max-w-full divide-y divide-white/10 border-y border-white/10" data-testid="admin-notifications-list">
        {loading ? (
          <div className="py-14 text-center text-sm text-zinc-500" data-testid="admin-notifications-loading">Memuat riwayat…</div>
        ) : data.items.length === 0 ? (
          <div className="py-16 text-center" data-testid="admin-notifications-empty">
            <BellRing className="mx-auto h-8 w-8 text-zinc-700" />
            <p className="mt-3 text-sm text-zinc-500">Tidak ada notifikasi yang cocok.</p>
          </div>
        ) : data.items.map((item) => (
          <NotificationRow
            key={item.id}
            item={item}
            showRecipient={scope === "all"}
            onMarkRead={(selected) => markRead(selected)}
            onOpen={(selected) => markRead(selected, true)}
          />
        ))}
      </section>

      <NotificationPagination page={data.page || page} pages={pages} onPageChange={setPage} />
    </div>
  );
}