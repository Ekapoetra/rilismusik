import React, { useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setDone(true);
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || "Gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen rm-mesh flex items-center justify-center px-4 py-12 text-white">
      <div className="w-full max-w-md rm-glass-strong rounded-[28px] p-8 rm-fade-up">
        <Link to="/login" className="text-sm text-zinc-400 hover:text-white">← Kembali ke Login</Link>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter mt-3">Lupa Password</h1>
        <p className="text-sm text-zinc-400 mt-2">Kami akan kirim link reset ke email Anda.</p>
        {done ? (
          <div className="mt-6" data-testid="forgot-password-done">
            <div className="rounded-2xl bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-4 py-3 text-sm">
              Jika email <b>{email}</b> terdaftar, link reset password sudah dikirim. Silakan cek inbox / folder spam Anda. Link berlaku 1 jam.
            </div>
            <Link to="/login" className="block mt-4 text-center text-sm rm-gradient-text font-semibold">Kembali ke Login →</Link>
          </div>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label className="rm-label">Email</label>
              <input type="email" className="rm-input" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="forgot-password-email-input" />
            </div>
            {err && <div role="alert" className="text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-xl px-3 py-2" data-testid="forgot-password-error">{err}</div>}
            <button className="rm-btn-primary w-full" disabled={loading} data-testid="forgot-password-submit-button">
              {loading ? "Memproses…" : "Kirim Link Reset"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
