import React, { useState, useEffect } from "react";
import { UserCheck, UserX, Sparkles } from "lucide-react";
import { api } from "@/api/client";

export default function AdminMigrate() {
  return (
    <div className="space-y-6" data-testid="admin-claims-page">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Klaim Akun</h1>
        <p className="text-sm text-zinc-400 mt-1">
          Resolve permintaan label untuk klaim akun label lama. <b>Super Admin only.</b>
        </p>
      </div>

      <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm text-emerald-200 flex items-start gap-2" data-testid="admin-autosync-info">
        <Sparkles className="w-4 h-4 flex-shrink-0 mt-0.5" />
        <span>
          Data <b>Label, Artis, Katalog (Release + Track), dan Riwayat Royalti</b> kini otomatis dibuat &
          disinkronkan saat upload CSV royalti Believe di halaman <b>Royalti</b> — tool migrasi manual lama sudah dihapus.
        </span>
      </div>

      <div className="rm-card p-5">
        <ClaimsPanel />
      </div>
    </div>
  );
}

function ClaimsPanel() {
  const [claims, setClaims] = useState([]);
  const [search, setSearch] = useState("");
  const [unclaimed, setUnclaimed] = useState([]);
  const [activeClaim, setActiveClaim] = useState(null);
  const [loading, setLoading] = useState(false);

  const reload = async () => {
    const { data } = await api.get("/admin/migrate/claims");
    setClaims(data);
  };
  useEffect(() => { reload(); }, []);

  const openLink = async (claim) => {
    setActiveClaim(claim);
    const { data } = await api.get(`/admin/migrate/labels/unclaimed?q=${encodeURIComponent(claim.claim_legacy_name || "")}`);
    setUnclaimed(data);
    setSearch(claim.claim_legacy_name || "");
  };
  const searchAgain = async () => {
    const { data } = await api.get(`/admin/migrate/labels/unclaimed?q=${encodeURIComponent(search)}`);
    setUnclaimed(data);
  };
  const doLink = async (legacy) => {
    setLoading(true);
    try {
      await api.post(`/admin/migrate/claims/${activeClaim.id}/link/${legacy.id}`);
      setActiveClaim(null); setUnclaimed([]); await reload();
    } catch (e) {
      alert(e.response?.data?.detail || "Link gagal");
    } finally { setLoading(false); }
  };
  const doReject = async (claim) => {
    const reason = window.prompt("Alasan reject?", "Data tidak cocok");
    if (reason === null) return;
    const fd = new FormData(); fd.append("reason", reason);
    await api.post(`/admin/migrate/claims/${claim.id}/reject`, fd, { headers: { "Content-Type": "multipart/form-data" } });
    await reload();
  };

  return (
    <div className="space-y-5">
      <div className="text-xs text-zinc-400">
        Total pending claims: <b className="text-zinc-200">{claims.length}</b>
      </div>

      {claims.length === 0 ? (
        <div className="text-center text-zinc-500 py-10 text-sm">
          <UserCheck className="w-8 h-8 mx-auto mb-2 opacity-50" />
          Belum ada permintaan claim akun lama.
        </div>
      ) : (
        <div className="space-y-3">
          {claims.map((c) => (
            <div key={c.id} className="rounded-2xl border border-white/5 bg-white/[0.02] p-4 flex flex-wrap items-start justify-between gap-3" data-testid={`admin-claim-${c.id}`}>
              <div className="text-sm space-y-1">
                <div className="font-semibold">{c.name} <span className="text-zinc-500 text-xs">· {c.email}</span></div>
                <div className="text-xs text-zinc-400">
                  Klaim sebagai: <b className="text-zinc-200">{c.claim_legacy_name}</b>
                </div>
                <div className="text-xs text-zinc-500">
                  Nama baru: {c.claim_label_name_new} · WA: {c.claim_whatsapp}
                </div>
                <div className="text-[10px] text-zinc-600">Diajukan: {c.claim_requested_at?.slice(0, 16)?.replace("T", " ")}</div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => openLink(c)}
                  className="rm-btn-primary text-xs flex items-center gap-2"
                  data-testid={`admin-claim-link-${c.id}`}
                >
                  <UserCheck className="w-3.5 h-3.5" /> Link
                </button>
                <button
                  onClick={() => doReject(c)}
                  className="rm-btn-secondary text-xs flex items-center gap-2 text-red-300"
                  data-testid={`admin-claim-reject-${c.id}`}
                >
                  <UserX className="w-3.5 h-3.5" /> Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeClaim && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="rm-card max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="text-lg font-bold">Link ke Legacy Label</div>
                <div className="text-xs text-zinc-400 mt-1">
                  Klaimer: <b>{activeClaim.email}</b> mengaku punya label <b className="text-zinc-200">{activeClaim.claim_legacy_name}</b>
                </div>
              </div>
              <button onClick={() => { setActiveClaim(null); setUnclaimed([]); }} className="text-zinc-400 hover:text-white text-xl">×</button>
            </div>
            <div className="flex gap-2 mb-3">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="rm-input flex-1"
                placeholder="Cari nama label lama…"
              />
              <button onClick={searchAgain} className="rm-btn-secondary text-xs px-4">Cari</button>
            </div>
            <div className="space-y-2">
              {unclaimed.length === 0 && (
                <div className="text-center text-zinc-500 text-sm py-6">Tidak ditemukan legacy label unclaimed.</div>
              )}
              {unclaimed.map((lab) => (
                <div key={lab.id} className="rounded-xl border border-white/5 bg-white/[0.02] p-3 flex items-center justify-between gap-3">
                  <div className="text-sm">
                    <div className="font-semibold">{lab.label_name}</div>
                    <div className="text-xs text-zinc-500">{lab.city || "—"} · PIC: {lab.pic_name || "—"} · {lab.subscription_tier || "no sub"}</div>
                  </div>
                  <button
                    onClick={() => doLink(lab)}
                    disabled={loading}
                    className="rm-btn-primary text-xs"
                    data-testid={`admin-claim-link-confirm-${lab.id}`}
                  >
                    Link
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
