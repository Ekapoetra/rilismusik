import React, { useState, useEffect } from "react";
import { UserCheck, UserX, Sparkles, ShieldAlert, Lock } from "lucide-react";
import { api } from "@/api/client";
import { useAuth } from "@/api/AuthContext";

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
      <QuarantinePanel />
    </div>
  );
}

function ClaimsPanel() {
  const { user } = useAuth();
  const isSuper = user?.role === "super_admin";
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
                <div className="font-semibold flex items-center gap-2">
                  {c.name} <span className="text-zinc-500 text-xs">· {c.email}</span>
                  {c.claim_status === "conflict" && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 px-2 py-0.5 text-[10px] font-medium" data-testid={`admin-claim-conflict-${c.id}`}>
                      <ShieldAlert className="w-3 h-3" /> Sengketa
                    </span>
                  )}
                </div>
                <div className="text-xs text-zinc-400">
                  Klaim sebagai: <b className="text-zinc-200">{c.claim_legacy_name}</b>
                </div>
                <div className="text-xs text-zinc-500">
                  Nama baru: {c.claim_label_name_new} · WA: {c.claim_whatsapp}
                </div>
                {c.claim_evidence_note && (
                  <div className="text-xs text-zinc-500">Bukti: <span className="text-zinc-300">{c.claim_evidence_note}</span></div>
                )}
                <div className="text-[10px] text-zinc-600">Diajukan: {c.claim_requested_at?.slice(0, 16)?.replace("T", " ")}</div>
              </div>
              <div className="flex gap-2">
                {isSuper ? (
                  <>
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
                  </>
                ) : (
                  <span className="text-[11px] text-zinc-500 flex items-center gap-1" data-testid={`admin-claim-super-only-${c.id}`}>
                    <Lock className="w-3 h-3" /> Hanya Super Admin
                  </span>
                )}
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

function QuarantinePanel() {
  const { user } = useAuth();
  const isSuper = user?.role === "super_admin";
  const [labels, setLabels] = useState([]);

  const reload = async () => {
    const { data } = await api.get("/admin/migrate/labels/quarantined");
    setLabels(data);
  };
  useEffect(() => { reload().catch(() => {}); }, []);

  const release = async (lab) => {
    if (!window.confirm(`Sahkan saldo warisan label '${lab.label_name}'? Pencairan akan dibuka untuk pemiliknya.`)) return;
    try {
      await api.post(`/admin/migrate/labels/${lab.id}/release-quarantine`);
      await reload();
    } catch (e) {
      alert(e.response?.data?.detail || "Gagal mengesahkan baseline");
    }
  };

  if (labels.length === 0) return null;
  return (
    <div className="rm-card p-5 space-y-3" data-testid="admin-quarantine-panel">
      <div className="flex items-center gap-2 font-semibold text-sm">
        <Lock className="w-4 h-4 text-amber-300" /> Saldo Warisan Dikarantina
      </div>
      <p className="text-xs text-zinc-500">
        Label hasil klaim yang baru dilink — pencairan diblokir sampai Super Admin mengesahkan baseline saldo warisan.
      </p>
      <div className="space-y-2">
        {labels.map((lab) => (
          <div key={lab.id} className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 flex items-center justify-between gap-3" data-testid={`admin-quarantine-${lab.id}`}>
            <div className="text-sm">
              <div className="font-semibold">{lab.label_name}</div>
              <div className="text-xs text-zinc-500">{lab.email || "—"} · dilink: {lab.claim_resolved_at?.slice(0, 10) || "—"}</div>
            </div>
            {isSuper ? (
              <button onClick={() => release(lab)} className="rm-btn-primary text-xs" data-testid={`admin-quarantine-release-${lab.id}`}>
                Sahkan Baseline
              </button>
            ) : (
              <span className="text-[11px] text-zinc-500 flex items-center gap-1"><Lock className="w-3 h-3" /> Hanya Super Admin</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
