import React from "react";
import { ArrowUpRight, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

export const number = (value) => value == null || !Number.isFinite(Number(value)) ? "—" : Number(value).toLocaleString("id-ID", { maximumFractionDigits: 1 });
export const rupiah = (value) => value == null ? "—" : `Rp ${number(value)}`;
export const dateWib = (value, options = {}) => value && !Number.isNaN(new Date(value).getTime()) ? new Date(value).toLocaleDateString("id-ID", { timeZone: "Asia/Jakarta", day: "numeric", month: "short", year: "numeric", ...options }) : "—";
export const timeWib = (value) => value && !Number.isNaN(new Date(value).getTime()) ? new Date(value).toLocaleTimeString("id-ID", { timeZone: "Asia/Jakarta", hour: "2-digit", minute: "2-digit" }) : "—";
export const monthWib = () => { const parts = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Jakarta", year: "numeric", month: "2-digit" }).formatToParts(new Date()); return `${parts.find(p => p.type === "year").value}-${parts.find(p => p.type === "month").value}`; };
export function ResourceState({ resource, empty, children }) {
  if (resource.loading && !resource.data) return <div className="v7-empty" role="status">Memuat data…</div>;
  if (resource.error) return <div className="v7-error" role="alert"><span>{resource.error}</span><button type="button" onClick={resource.reload}><RefreshCw size={14} /> Coba lagi</button></div>;
  if (!resource.data) return <div className="v7-empty">{empty || "Data belum tersedia."}</div>;
  return children;
}
export function Panel({ title, subtitle, action, children, className = "" }) {
  return <section className={`v7-panel ${className}`}><div className="v7-panel-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>;
}
export function MoreLink({ to, children = "Lihat semua" }) { return <Link className="v7-text-link" to={to}>{children}<ArrowUpRight size={15} /></Link>; }
export function WorkRow({ item, progress = false }) {
  return <Link to={item.link} className="v7-work-row"><span className="v7-work-copy"><strong>{item.title}</strong><small>{item.label_name ? `${item.label_name} · ` : ""}{item.category}</small><span className={`v7-badge ${item.waiting ? "is-waiting" : ""}`}>{item.status_label}</span></span>{progress && <span className="v7-progress-cell">{item.percent == null ? <small>Belum terukur</small> : <><span className="v7-progress"><i style={{ width: `${Math.max(0, Math.min(100, item.percent))}%` }} /></span><small>{item.percent}%</small></>}</span>}<ArrowUpRight size={17} /></Link>;
}
