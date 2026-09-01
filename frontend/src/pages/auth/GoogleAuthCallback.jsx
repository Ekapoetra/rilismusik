import React, { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth, formatApiError } from "@/api/AuthContext";
import { LogoFull } from "@/components/shared/Brand";

export default function GoogleAuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const { exchangeGoogleSession } = useAuth();
  const processed = useRef(false);
  const [error, setError] = useState("");
  const sessionId = new URLSearchParams((location.hash || "").replace(/^#/, "")).get("session_id");

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    if (!sessionId) { setError("Session Google tidak ditemukan."); return; }
    exchangeGoogleSession(sessionId)
      .then(() => navigate("/label/dashboard", { replace: true }))
      .catch((err) => setError(formatApiError(err.response?.data?.detail) || "Google Login gagal"));
  }, [exchangeGoogleSession, navigate, sessionId]);

  return <div className="min-h-screen rm-mesh flex items-center justify-center px-4 py-12 text-white" data-testid="google-auth-callback">
    <div className="w-full max-w-md rm-glass-strong rounded-[28px] p-8 text-center rm-fade-up">
      <LogoFull width={160} className="mx-auto" />
      {error ? <div className="mt-6" role="alert" data-testid="google-auth-callback-error"><h1 className="font-display text-2xl font-extrabold">Google Login gagal</h1><p className="mt-3 text-sm text-red-300">{error}</p><p className="mt-2 text-xs text-zinc-500">Google Login hanya untuk akun label yang sudah terdaftar dengan email yang sama.</p><div className="mt-6 flex justify-center gap-3"><Link to="/login" className="rm-btn-ghost" data-testid="google-auth-back-login">Login</Link><Link to="/register" className="rm-btn-primary" data-testid="google-auth-back-register">Daftar</Link></div></div> : <div className="mt-8" data-testid="google-auth-callback-loading"><Loader2 className="mx-auto h-8 w-8 animate-spin text-[#FF1F8E]" /><h1 className="mt-4 font-display text-xl font-extrabold">Menghubungkan akun Google…</h1><p className="mt-2 text-sm text-zinc-500">Mohon tunggu, jangan tutup halaman ini.</p></div>}
    </div>
  </div>;
}