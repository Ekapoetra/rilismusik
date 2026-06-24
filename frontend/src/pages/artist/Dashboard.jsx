import React, { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/api/AuthContext";
import { api } from "@/api/client";
import { LogOut, Music, Building2 } from "lucide-react";

export default function ArtistDashboard() {
  const { user, profile, logout } = useAuth();
  const navigate = useNavigate();
  const [releases, setReleases] = useState([]);

  useEffect(() => {
    api.get("/releases/").then((r) => setReleases(r.data));
  }, []);

  const onLogout = async () => { await logout(); navigate("/login"); };
  const vis = profile?.visibility_settings || {};

  return (
    <div className="min-h-screen rm-mesh-dim p-4 md:p-8">
      <div className="max-w-3xl mx-auto space-y-5">
        <div className="flex justify-between items-center">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-2xl bg-[#FF3B30] text-white grid place-items-center font-bold">R</div>
            <span className="font-display font-extrabold tracking-tight">RILIS MUSIK</span>
          </Link>
          <button onClick={onLogout} className="text-sm flex items-center gap-1.5 text-slate-600 hover:text-red-600" data-testid="artist-logout">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>

        <div className="rm-card p-6">
          <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Artist Dashboard</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter mt-1">Halo, {profile?.artist_name || user?.name}</h1>
          <div className="text-sm text-slate-600 mt-1">{user?.email}</div>
          <div className="mt-3 text-xs flex items-center gap-1.5 text-slate-500"><Building2 className="w-3.5 h-3.5" /> Label terhubung</div>
        </div>

        <div className="rm-card p-5">
          <h3 className="font-display font-bold text-lg tracking-tight mb-3">Lagu Saya</h3>
          {releases.length === 0 ? (
            <div className="text-sm text-slate-500 text-center py-6">Belum ada lagu yang dikaitkan. Hubungi label Anda.</div>
          ) : (
            <div className="divide-y divide-slate-100">
              {releases.map((r) => (
                <div key={r.id} className="py-3 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-400 to-pink-500 grid place-items-center text-white"><Music className="w-4 h-4" /></div>
                  <div className="min-w-0">
                    <div className="font-semibold text-sm truncate">{r.release_title}</div>
                    <div className="text-xs text-slate-500">{r.artist_name} • {r.release_date}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rm-card p-5">
          <h3 className="font-display font-bold text-lg tracking-tight mb-2">Pengaturan Visibilitas (dari Label)</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <Vis k="Lihat nominal royalti" v={vis.show_amount} />
            <Vis k="Lihat persentase" v={vis.show_percentage} />
            <Vis k="Lihat per lagu" v={vis.show_per_song} />
            <Vis k="Histori bulanan" v={vis.show_monthly_history} />
          </div>
          <div className="text-[11px] text-slate-500 mt-3">Royalti detail akan tersedia setelah laporan CSV pertama dipublikasikan admin. (Fase 2)</div>
        </div>
      </div>
    </div>
  );
}
function Vis({ k, v }) { return <div className={`rounded-lg p-2 ${v ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}><div className="font-semibold">{k}</div><div className="text-[10px]">{v ? "Diizinkan" : "Disembunyikan"}</div></div>; }
