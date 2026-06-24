import React, { useEffect, useState } from "react";
import { api, fileUrl } from "@/api/client";
import { FileSignature, Download, AlertTriangle, CheckCircle2, Clock, Ban } from "lucide-react";

const STATUS_LABELS = {
  active: "Aktif",
  expiring_soon: "Akan Berakhir",
  expired: "Kadaluarsa",
  terminated: "Diakhiri",
};

const STATUS_STYLES = {
  active: { bg: "rgba(16,185,129,0.18)", color: "#6EE7B7", dot: "#10B981", Icon: CheckCircle2 },
  expiring_soon: { bg: "rgba(245,158,11,0.18)", color: "#FCD34D", dot: "#F59E0B", Icon: Clock },
  expired: { bg: "rgba(239,68,68,0.18)", color: "#FCA5A5", dot: "#EF4444", Icon: AlertTriangle },
  terminated: { bg: "rgba(255,255,255,0.06)", color: "#A1A1B5", dot: "#71717A", Icon: Ban },
};

export default function LabelContract() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    api.get("/contracts/label").then(({ data }) => setItems(data)).catch(() => {});
  }, []);

  const active = items.filter((c) => c.effective_status === "active" || c.effective_status === "expiring_soon");
  const past = items.filter((c) => c.effective_status === "expired" || c.effective_status === "terminated");

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Legal</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Kontrak Distribusi</h1>
        <p className="text-sm text-zinc-400 mt-1">Kontrak kerja sama Anda dengan RILIS MUSIK. Setiap kontrak hanya bisa dikelola oleh admin.</p>
      </div>

      {items.length === 0 && (
        <div className="rm-card p-10 text-center text-zinc-500">
          <FileSignature className="w-10 h-10 mx-auto mb-3 text-zinc-700" />
          <div className="text-sm">Belum ada kontrak. Hubungi admin RILIS MUSIK.</div>
        </div>
      )}

      {active.length > 0 && (
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Kontrak Aktif</div>
          {active.map((c) => <ContractCard key={c.id} c={c} />)}
        </div>
      )}

      {past.length > 0 && (
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Riwayat Kontrak</div>
          {past.map((c) => <ContractCard key={c.id} c={c} />)}
        </div>
      )}
    </div>
  );
}

function ContractCard({ c }) {
  const s = STATUS_STYLES[c.effective_status] || STATUS_STYLES.active;
  const Icon = s.Icon;
  return (
    <div className="rm-card p-5" data-testid={`label-contract-card-${c.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-12 h-12 rounded-xl grid place-items-center" style={{ background: s.bg, color: s.color }}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <div className="font-display font-extrabold text-lg tracking-tighter">{c.filename || "Kontrak Distribusi"}</div>
            <div className="text-xs text-zinc-500">Dibuat {new Date(c.created_at).toLocaleDateString("id-ID")}</div>
          </div>
        </div>
        <span className="rm-badge" style={{ background: s.bg, color: s.color }}>
          <span className="rm-badge-dot" style={{ background: s.dot }} />
          {STATUS_LABELS[c.effective_status]}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Mulai</div>
          <div className="font-semibold">{c.start_date}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Berakhir</div>
          <div className="font-semibold">
            {c.is_lifetime || !c.end_date ? (
              <span className="text-emerald-300">Tanpa Batas Waktu</span>
            ) : c.end_date}
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Sisa</div>
          <div className="font-semibold">
            {c.effective_status === "terminated" ? "—" :
              c.is_lifetime || c.days_left === null ? (
                <span className="text-zinc-400">Lifetime</span>
              ) : (
                <span className={c.days_left < 0 ? "text-red-300" : c.days_left <= 30 ? "text-amber-300" : ""}>
                  {c.days_left < 0 ? `${Math.abs(c.days_left)} hari lewat` : `${c.days_left} hari`}
                </span>
              )}
          </div>
        </div>
        <div className="flex items-end">
          <a
            href={fileUrl(c.file_url)}
            target="_blank"
            rel="noreferrer"
            className="rm-btn-primary text-xs flex items-center gap-2 px-3 py-2"
            data-testid={`label-contract-download-${c.id}`}
          >
            <Download className="w-3.5 h-3.5" /> Download PDF
          </a>
        </div>
      </div>

      {c.kind === "mda" && (
        <div className="mt-4 rounded-xl bg-violet-500/10 border border-violet-500/20 p-3 text-xs text-violet-200 flex items-start gap-2">
          <FileSignature className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>
            <b>Master Distribution Agreement</b> — disetujui via checkbox elektronik pada {c.accepted_at?.slice(0, 10)} oleh <b>{c.accepted_by_name}</b>. UU ITE No. 11/2008.
          </span>
        </div>
      )}

      {c.notes && (
        <div className="mt-4 rounded-xl bg-white/[0.03] border border-white/5 p-3 text-xs text-zinc-400">
          <div className="font-bold text-zinc-300 mb-1">Catatan</div>
          {c.notes}
        </div>
      )}

      {c.effective_status === "terminated" && c.terminated_reason && (
        <div className="mt-4 rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-xs">
          <div className="font-bold text-red-300 mb-1">Alasan Pengakhiran</div>
          <div className="text-red-200">{c.terminated_reason}</div>
        </div>
      )}

      {c.effective_status === "expiring_soon" && (
        <div className="mt-4 rounded-xl bg-amber-500/10 border border-amber-500/20 p-3 text-xs text-amber-200 flex items-start gap-2">
          <Clock className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>Kontrak akan berakhir dalam {c.days_left} hari. Hubungi admin untuk perpanjangan.</span>
        </div>
      )}
    </div>
  );
}
