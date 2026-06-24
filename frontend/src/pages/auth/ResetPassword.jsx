import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, formatApiError } from "@/api/client";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [token, setToken] = useState(params.get("token") || "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (password !== confirm) { setErr("Password tidak cocok"); return; }
    if (password.length < 8) { setErr("Password minimal 8 karakter"); return; }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, password });
      setDone(true);
      setTimeout(() => navigate("/login"), 1500);
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || "Gagal reset password");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen rm-mesh flex items-center justify-center px-4 py-12 text-white">
      <div className="w-full max-w-md rm-glass-strong rounded-[28px] p-8 rm-fade-up">
        <Link to="/login" className="text-sm text-zinc-400 hover:text-white">← Login</Link>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter mt-3">Reset Password</h1>
        {done ? (
          <div className="mt-6 text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 text-sm">Password berhasil direset. Mengalihkan ke login…</div>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label className="rm-label">Token</label>
              <input className="rm-input" value={token} onChange={(e) => setToken(e.target.value)} required data-testid="reset-token-input" />
            </div>
            <div>
              <label className="rm-label">Password Baru</label>
              <input type="password" className="rm-input" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} data-testid="reset-password-input" />
            </div>
            <div>
              <label className="rm-label">Konfirmasi Password</label>
              <input type="password" className="rm-input" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} data-testid="reset-password-confirm-input" />
            </div>
            {err && <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-xl px-3 py-2">{err}</div>}
            <button className="rm-btn-primary w-full" disabled={loading} data-testid="reset-submit-button">
              {loading ? "Memproses…" : "Reset Password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
