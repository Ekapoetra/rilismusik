import React, { useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [token, setToken] = useState("");
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email });
      setDone(true);
      if (data.reset_token) setToken(data.reset_token);
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || "Gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen rm-mesh flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md rm-glass-strong rounded-[28px] p-8 rm-fade-up">
        <Link to="/login" className="text-sm text-slate-600 hover:text-[#FF3B30]">← Kembali ke Login</Link>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter mt-3">Lupa Password</h1>
        <p className="text-sm text-slate-600 mt-2">Kami akan kirim link reset ke email Anda.</p>
        {done ? (
          <div className="mt-6">
            <div className="rounded-2xl bg-emerald-50 text-emerald-700 px-4 py-3 text-sm">Jika email terdaftar, link reset telah dikirim.</div>
            {token && (
              <div className="mt-3 text-xs bg-slate-50 rounded-xl p-3">
                <div className="font-semibold">[DEV] Reset token:</div>
                <code className="block mt-1 break-all">{token}</code>
                <Link to={`/reset-password?token=${token}`} className="block mt-2 font-semibold text-[#FF3B30]" data-testid="forgot-password-dev-link">
                  Lanjut ke Reset Password →
                </Link>
              </div>
            )}
          </div>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label className="rm-label">Email</label>
              <input type="email" className="rm-input" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="forgot-password-email-input" />
            </div>
            {err && <div className="text-sm text-red-600 bg-red-50 rounded-xl px-3 py-2">{err}</div>}
            <button className="rm-btn-primary w-full" disabled={loading} data-testid="forgot-password-submit-button">
              {loading ? "Memproses…" : "Kirim Link Reset"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
