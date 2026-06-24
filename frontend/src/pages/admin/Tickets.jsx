import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fileUrl } from "@/api/client";
import TicketStatusBadge, { TICKET_CATEGORY_LABELS, TICKET_STATUS_LABELS } from "@/components/shared/TicketStatusBadge";
import { ADMIN_TICKET } from "@/constants/testIds";
import { Search, MessageSquare } from "lucide-react";

const STATUSES = Object.keys(TICKET_STATUS_LABELS);
const CATEGORIES = Object.keys(TICKET_CATEGORY_LABELS);

export default function AdminTickets() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [q, setQ] = useState("");

  const load = async () => {
    const { data } = await api.get("/tickets/admin", {
      params: { status: status || undefined, category: category || undefined, q: q || undefined },
    });
    setItems(data);
  };

  useEffect(() => { load(); }, [status, category]);

  return (
    <div className="space-y-5 max-w-7xl">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Support</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Support Tickets</h1>
        <p className="text-sm text-zinc-400 mt-1">Takedown, edit metadata/audio/cover, Content ID, royalti.</p>
      </div>

      <div className="rm-card p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[220px]">
          <label className="rm-label">Cari</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
            <input
              className="rm-input pl-10"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && load()}
              placeholder="Cari subjek / nomor tiket"
              data-testid={ADMIN_TICKET.search}
            />
          </div>
        </div>
        <div className="min-w-[180px]">
          <label className="rm-label">Status</label>
          <select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid={ADMIN_TICKET.statusFilter}>
            <option value="">Semua</option>
            {STATUSES.map((s) => <option key={s} value={s}>{TICKET_STATUS_LABELS[s]}</option>)}
          </select>
        </div>
        <div className="min-w-[200px]">
          <label className="rm-label">Kategori</label>
          <select className="rm-input" value={category} onChange={(e) => setCategory(e.target.value)} data-testid={ADMIN_TICKET.categoryFilter}>
            <option value="">Semua</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{TICKET_CATEGORY_LABELS[c]}</option>)}
          </select>
        </div>
        <button className="rm-btn-ghost" onClick={load}>Apply</button>
      </div>

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-2">No. Tiket</div>
          <div className="col-span-2">Label</div>
          <div className="col-span-2">Kategori</div>
          <div className="col-span-3">Rilisan / Subjek</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? (
          <div className="p-10 text-center text-zinc-500 text-sm">
            <MessageSquare className="w-8 h-8 mx-auto mb-3 text-zinc-700" />
            Tidak ada tiket.
          </div>
        ) : items.map((t) => (
          <Link
            key={t.id}
            to={`/admin/tickets/${t.id}`}
            className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0 hover:bg-white/[0.02]"
            data-testid={`admin-ticket-row-${t.id}`}
          >
            <div className="col-span-12 md:col-span-2">
              <div className="font-display font-bold text-sm">{t.ticket_no}</div>
              <div className="text-xs text-zinc-500">{new Date(t.created_at).toLocaleDateString("id-ID")}</div>
            </div>
            <div className="col-span-6 md:col-span-2 text-sm truncate">{t.label_name || "—"}</div>
            <div className="col-span-6 md:col-span-2 text-sm">{TICKET_CATEGORY_LABELS[t.category] || t.category}</div>
            <div className="col-span-12 md:col-span-3 flex items-center gap-2 min-w-0">
              {t.release_cover_url && <img src={fileUrl(t.release_cover_url)} alt="" className="w-8 h-8 rounded object-cover" />}
              <div className="min-w-0">
                <div className="text-xs text-zinc-400 truncate">{t.release_title}</div>
                <div className="text-sm truncate">{t.subject}</div>
              </div>
            </div>
            <div className="col-span-6 md:col-span-2"><TicketStatusBadge status={t.status} /></div>
            <div className="col-span-6 md:col-span-1 text-right text-sm font-semibold rm-gradient-text">Detail →</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
