import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Check, ChevronDown, ChevronRight, ChevronUp, Info, Layers, X } from "lucide-react";
import { sharedRead } from "@/api/sharedRead";
import { api } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { useLabelKyc } from "@/contexts/LabelKycContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { useMasthead } from "@/components/v13/Masthead";
import StatusBadge from "@/components/shared/StatusBadge";
import { LABEL_DASHBOARD } from "@/constants/testIds";
import { planName } from "@/lib/plans";

const idr = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
const num = (n) => new Intl.NumberFormat("id-ID").format(n || 0);
const when = (iso) => (iso ? new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Jakarta" }) : "");

// Prototype labelHome102 groups, mapped to production release statuses.
const IN_PROCESS = ["submitted", "awaiting_payment", "paid", "under_review", "approved", "delivered", "takedown_requested"];
const GROUPS = [
  { key: "total", name: "Total rilisan", match: () => true },
  { key: "draft", name: "Draft", match: (r) => r.status === "draft" },
  { key: "process", name: "Dalam penanganan", match: (r) => IN_PROCESS.includes(r.status) },
  { key: "revision", name: "Perlu perbaikan", match: (r) => r.status === "need_revision" || r.status === "rejected" },
  { key: "live", name: "Tayang", match: (r) => r.status === "live" },
];
const MODE_NAME = { express: "Express", max: "MAX" };

function Chevron({ direction = "right" }) {
  const Icon = { right: ChevronRight, down: ChevronDown, up: ChevronUp }[direction];
  return <span className="v13-chevron" aria-hidden="true"><Icon /></span>;
}

function Attention({ item, onDismiss }) {
  const Icon = item.tone === "info" ? Info : AlertTriangle;
  const body = <><Icon aria-hidden="true" /><div className="min-w-0"><h3>{item.title}</h3><p>{item.text}</p></div>{item.to ? <Chevron /> : <span />}</>;
  return <div className="relative">
    {item.to ? <Link to={item.to} className="v13-attention" data-tone={item.tone} data-testid={`label-attention-${item.key}`}>{body}</Link> : <div className="v13-attention" data-tone={item.tone} data-testid={`label-attention-${item.key}`}>{body}</div>}
    {onDismiss && <button type="button" onClick={onDismiss} className="absolute right-14 top-1/2 -translate-y-1/2 rounded-full p-1 text-[var(--ui-muted)] hover:text-[var(--ui-text)]" aria-label="Tutup"><X className="h-4 w-4" /></button>}
  </div>;
}

function ActivationBar({ kyc }) {
  const { t } = useAppPreferences();
  if (!kyc || kyc.is_verified) return null;
  const done = (key) => kyc.checks?.find((item) => item.key === key)?.complete;
  const identity = ["pic_name", "label_name", "logo", "email", "whatsapp", "address", "city"].every(done) && ["pending_review", "verified"].includes(kyc.document?.status);
  const steps = [
    ["Identitas Label", identity],
    ["Rekening", done("bank")],
    ["Kontrak", done("contract")],
    ["Pemeriksaan", kyc.is_verified],
  ];
  const reviewing = kyc.status === "pending_review";
  return <section className="v13-card flex flex-wrap items-center gap-5 p-5" data-testid={LABEL_DASHBOARD.verifyWarning || "label-dashboard-verify-warning"}>
    <div className="min-w-[200px] flex-1"><h2 className="text-lg font-medium">{t(reviewing ? "Akun sedang diperiksa" : "Aktivasi akun")}</h2><p className="mt-1 text-sm text-[var(--ui-muted)]">{t(reviewing ? "Tim Rilis Musik sedang memeriksa identitasmu." : kyc.status === "rejected" ? `Perlu diperbaiki: ${kyc.rejection_reason || "periksa catatan di Profil Label"}` : "Lengkapi langkah berikut untuk membuka seluruh fitur label.")}</p></div>
    <ol className="flex flex-wrap items-center gap-3 text-sm">{steps.map(([name, ok], index) => <li key={name} className="flex items-center gap-2"><span className={`grid h-6 w-6 place-items-center rounded-full text-xs ${ok ? "bg-[#3a8dff] text-white" : "border border-[var(--ui-border)] text-[var(--ui-muted)]"}`}>{ok ? <Check className="h-3.5 w-3.5" strokeWidth={3} /> : index + 1}</span>{t(name)}</li>)}</ol>
    <Link to="/label/profile" className="v13-plan-cta w-auto px-5" style={{ width: "auto" }} data-testid="label-dashboard-verify-cta">{t(reviewing ? "Lihat Status" : "Lanjutkan")}</Link>
  </section>;
}

function MultiLabelCard({ account, verified }) {
  const { t } = useAppPreferences();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const withdraw = async () => {
    setBusy(true); setMessage("");
    try { await api.post("/withdraw/label/batch"); setMessage(t("Pencairan gabungan diajukan untuk seluruh label.")); }
    catch (error) { setMessage(error?.response?.data?.detail || t("Pencairan gabungan gagal.")); }
    finally { setBusy(false); }
  };
  return <section className="v13-card flex flex-wrap items-center justify-between gap-4 p-5" data-testid="label-multi-label-bar">
    <div className="flex items-center gap-3"><Layers className="h-5 w-5 text-[var(--ui-muted)]" /><div><div className="text-sm font-semibold">{t("Multi Label")}</div><div className="text-sm text-[var(--ui-muted)]" data-testid="label-multi-label-summary">{account.label_count} {t("label dikelola dalam satu akun")}</div></div></div>
    <div className="flex flex-wrap items-center gap-4"><div className="text-right"><div className="text-xs text-[var(--ui-muted)]">{t("Total saldo tersedia")}</div><div className="text-xl tabular-nums" data-testid="label-account-available">{verified ? idr(account.account_available_idr) : "—"}</div></div>
      {verified && account.account_available_idr > 0 && <button type="button" onClick={withdraw} disabled={busy} className="v13-plan-cta px-5" style={{ width: "auto" }} data-testid="label-batch-withdraw-cta">{t("Cairkan semua label")}</button>}</div>
    {message && <p className="w-full text-sm text-[var(--ui-muted)]" role="status">{message}</p>}
  </section>;
}

export default function LabelDashboardHome() {
  const { user } = useAuth();
  const { t } = useAppPreferences();
  const { kyc } = useLabelKyc();
  const scope = JSON.stringify([user?.id, user?.active_label_id]);
  const [data, setData] = useState(null);
  const [account, setAccount] = useState(null);
  const [releases, setReleases] = useState(null);
  const [updates, setUpdates] = useState(null);
  const [bankRequests, setBankRequests] = useState([]);
  const [filter, setFilter] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [claimDismissed, setClaimDismissed] = useState(false);
  const verified = Boolean(kyc?.is_verified);

  useEffect(() => {
    let active = true;
    sharedRead(scope, "/label/dashboard").then((r) => { if (active) setData(r.data); }).catch(() => { if (active) setLoadError("Dashboard belum dapat dimuat. Muat ulang halaman untuk mencoba lagi."); });
    sharedRead(scope, "/label/account").then((r) => { if (active) setAccount(r.data); }).catch(() => {});
    api.get("/notifications/me", { params: { limit: 6 } }).then((r) => { if (active) setUpdates(r.data?.items || []); }).catch(() => { if (active) setUpdates([]); });
    api.get("/label/bank-account/change-requests").then((r) => { if (active) setBankRequests(Array.isArray(r.data) ? r.data : r.data?.items || []); }).catch(() => {});
    return () => { active = false; };
  }, [scope]);
  useEffect(() => {
    if (!verified) { setReleases(null); return undefined; }
    let active = true;
    sharedRead(scope, "/releases/", { limit: 500, include_revenue: false }).then((r) => { if (active) setReleases(Array.isArray(r.data) ? r.data : []); }).catch(() => { if (active) setReleases([]); });
    return () => { active = false; };
  }, [scope, verified]);
  useEffect(() => {
    if (data?.label?.id && localStorage.getItem(`rm:claim_dismissed:${data.label.id}`)) setClaimDismissed(true);
  }, [data?.label?.id]);

  const counts = useMemo(() => {
    if (releases) return Object.fromEntries(GROUPS.map((group) => [group.key, releases.filter(group.match).length]));
    const p = data?.pipeline || {};
    return { total: (p.draft || 0) + (p.review || 0) + (p.delivered || 0) + (p.live || 0), draft: p.draft || 0, process: (p.review || 0) + (p.delivered || 0), revision: null, live: p.live || 0 };
  }, [releases, data]);

  const summary = data ? `${num(counts.draft)} ${t("draft dan")} ${num(counts.process)} ${t("rilisan dalam proses saat ini.")}` : null;
  useMasthead({
    summary,
    insight: data ? { value: num(counts.live), title: t("Katalogmu terus berkembang."), detail: `${num(counts.total)} ${t("rilisan tersimpan dalam akun labelmu.")}`, to: "/label/releases" } : null,
  });

  if (!data && loadError) return <div role="alert" className="v13-card p-6 text-[var(--v13-urgent)]">{t(loadError)}</div>;
  if (!data) return <div className="space-y-4" data-testid="label-dashboard-loading">{[0, 1, 2].map((i) => <div key={i} className="h-28 animate-pulse rounded-2xl bg-[var(--ui-surface)]" />)}</div>;

  const stats = data.stats || {};
  const ent = account?.entitlements;
  const attention = [];
  for (const release of (releases || []).filter((item) => item.status === "need_revision").slice(0, 3)) {
    attention.push({ key: `revision-${release.id}`, tone: "red", title: t("Perbaikan rilisan menunggu"), text: `${release.release_title}${release.admin_note ? ` · ${release.admin_note}` : ""}`, to: `/label/releases/${release.id}/edit` });
  }
  const pendingBank = bankRequests.find((item) => item.status === "pending");
  if (pendingBank) attention.push({ key: "bank", tone: "info", title: t("Rekening sedang diperiksa"), text: t("Rekening saat ini tetap digunakan sampai rekening baru disetujui."), to: "/label/profile?tab=bank" });
  else if (!stats.bank_verified) attention.push({ key: "bank", tone: "mustard", title: t("Lengkapi rekening"), text: t("Rilisan dapat dikirim. Rekening diperlukan saat mengajukan pencairan."), to: "/label/profile?tab=bank" });
  if (stats.subscription_expires_at && ent && !ent.active && stats.payment_type === "annual_subscription") {
    attention.push({ key: "plan", tone: "mustard", title: `${t("Paket")} ${planName(data.label?.subscription_tier || "annual_normal")} ${t("berakhir")}`, text: t("Perpanjang paket untuk kembali merilis tanpa biaya per lagu."), to: "/label/invoices" });
  }
  if ((stats.pending_invoices || 0) > 0) attention.push({ key: "invoices", tone: "mustard", title: `${t("Pembayaran menunggu")} · ${stats.pending_invoices}`, text: t("Selesaikan pembayaran agar pesanan dapat diproses."), to: "/label/invoices" });
  if ((stats.active_tickets || 0) > 0) attention.push({ key: "tickets", tone: "info", title: `${t("Tiket bantuan aktif")} · ${stats.active_tickets}`, text: t("Lihat perkembangan tiket bantuanmu."), to: "/label/support" });
  if (user?.claim_status === "pending_link") attention.push({ key: "claim", tone: "info", title: t("Klaim label sedang diperiksa"), text: t("Admin sedang memproses klaim label lama Anda."), to: "/label/profile" });
  else if (user?.claim_status === "rejected") attention.push({ key: "claim", tone: "red", title: t("Klaim label perlu diperbaiki"), text: user?.claim_reject_reason || t("Ajukan klaim kembali untuk melihat royalti periode sebelumnya."), to: "/label/profile" });
  else if (user?.claim_status !== "linked" && !claimDismissed) attention.push({ key: "claim", tone: "info", title: t("Punya label lama di Rilis Musik?"), text: t("Klaim label untuk menautkan riwayat royalti dan penarikan sebelumnya."), to: "/label/profile", dismiss: () => { localStorage.setItem(`rm:claim_dismissed:${data.label.id}`, "1"); setClaimDismissed(true); } });

  const latest = (releases || []).slice().sort((a, b) => String(b.updated_at || b.created_at || "").localeCompare(String(a.updated_at || a.created_at || ""))).slice(0, 5);
  const group = GROUPS.find((item) => item.key === filter);
  const filtered = group && releases ? releases.filter(group.match) : [];

  return <div className="space-y-5" data-testid="label-dashboard">
    <h1 className="sr-only" data-testid="label-dashboard-name" translate="no">{data.label?.label_name}</h1>
    <ActivationBar kyc={kyc} />
    {account?.is_multi_label && <MultiLabelCard account={account} verified={verified} />}
    {attention.length > 0 && <div className="grid gap-3 lg:grid-cols-2">{attention.map((item) => <Attention key={item.key} item={item} onDismiss={item.dismiss} />)}</div>}

    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5" data-testid="label-release-stats">
      {GROUPS.map((item) => <button key={item.key} type="button" disabled={!releases} onClick={() => setFilter(filter === item.key ? null : item.key)} aria-expanded={filter === item.key} className="v13-stat text-left disabled:cursor-default" data-testid={item.key === "total" ? LABEL_DASHBOARD.totalReleases : `label-stat-${item.key}`}>
        <span>{t(item.name)}</span><strong>{counts[item.key] === null ? "—" : num(counts[item.key])}</strong><small>{t("Rilisan")}</small><Chevron direction={filter === item.key ? "up" : "down"} />
      </button>)}
    </div>
    {group && <section className="v13-card" data-testid="label-stat-filter">
      <div className="v13-card-head"><h2>{t(group.name)} · {filtered.length}</h2><button type="button" className="text-sm text-[var(--ui-muted)] hover:text-[var(--ui-text)]" onClick={() => setFilter(null)}>{t("Tutup filter")}</button></div>
      <div className="v13-card-body">{filtered.length === 0 ? <p className="py-4 text-sm text-[var(--ui-muted)]">{t("Tidak ada rilisan.")}</p> : filtered.slice(0, 20).map((release) => <ReleaseRow key={release.id} release={release} />)}</div>
    </section>}

    <div className="grid gap-5 lg:grid-cols-2">
      <section className="v13-card" data-testid="label-dashboard-releases">
        <div className="v13-card-head"><h2>{t("Rilisan Saya")}</h2><div className="flex items-center gap-3"><Link to="/label/releases/upload" className="v13-plan-cta px-4 py-2 text-sm" style={{ width: "auto" }} data-testid={LABEL_DASHBOARD.uploadReleaseButton}>{t("Buat rilisan")}</Link><Link to="/label/releases" className="text-sm text-[var(--ui-muted)] hover:text-[var(--ui-text)]">{t("Lihat semua")}</Link></div></div>
        <div className="v13-card-body">{!verified ? <p className="py-4 text-sm text-[var(--ui-muted)]">{t("Rilisan tampil setelah akun aktif.")}</p> : releases === null ? <p role="status" className="py-4 text-sm text-[var(--ui-muted)]">{t("Memuat rilisan…")}</p> : latest.length === 0 ? <p className="py-4 text-sm text-[var(--ui-muted)]">{t("Belum ada rilisan. Mulai dari rilisan pertamamu.")}</p> : latest.map((release) => <ReleaseRow key={release.id} release={release} />)}</div>
      </section>
      <section className="v13-card" data-testid="label-dashboard-updates">
        <div className="v13-card-head"><h2>{t("Pembaruan")}</h2></div>
        <div className="v13-card-body">{updates === null ? <p role="status" className="py-4 text-sm text-[var(--ui-muted)]">{t("Memuat pembaruan…")}</p> : updates.length === 0 ? <p className="py-4 text-sm text-[var(--ui-muted)]">{t("Belum ada pembaruan.")}</p> : updates.map((item) => {
          const inner = <><div className="min-w-0"><div className="v13-row-title truncate">{item.title}</div><div className="v13-row-sub line-clamp-2">{item.body}</div></div><span className="shrink-0 text-xs text-[var(--ui-muted)]">{when(item.created_at)}</span></>;
          return item.link && item.link.startsWith("/") ? <Link key={item.id} to={item.link} className="v13-row">{inner}</Link> : <div key={item.id} className="v13-row">{inner}</div>;
        })}</div>
      </section>
    </div>
  </div>;
}

function ReleaseRow({ release }) {
  const { t } = useAppPreferences();
  const tracks = release.track_count ?? release.tracks_count ?? release.track_identifiers?.length;
  const sub = [release.display_primary_artists?.join(", ") || release.artist_name, tracks ? `${tracks} ${t("lagu")}` : null, MODE_NAME[release.service_mode]].filter(Boolean).join(" · ");
  return <Link to={release.status === "draft" || release.status === "need_revision" ? `/label/releases/${release.id}/edit` : `/label/releases/${release.id}`} className="v13-row" data-testid={`label-release-row-${release.id}`}>
    <div className="min-w-0"><div className="v13-row-title truncate">{release.release_title || t("Tanpa judul")}</div><div className="v13-row-sub truncate">{sub}</div></div>
    <div className="flex shrink-0 items-center gap-3"><StatusBadge status={release.status} /><Chevron /></div>
  </Link>;
}
