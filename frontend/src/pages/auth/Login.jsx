import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth, formatApiError } from "@/api/AuthContext";
import { LOGIN } from "@/constants/testIds";
import { LogoFull } from "@/components/shared/Brand";

function roleHome(role) {
  if (role === "label") return "/label/dashboard";
  if (role === "artist") return "/artist/dashboard";
  if (["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content"].includes(role)) return "/admin/dashboard";
  return "/";
}

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const data = await login(email, password);
      const next = loc.state?.from || roleHome(data.user.role);
      navigate(next, { replace: true });
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || "Login gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen rm-mesh flex items-center justify-center px-4 py-12 text-white">
      <div className="w-full max-w-md rm-glass-strong rounded-[28px] p-8 md:p-10 rm-fade-up">
        <Link to="/" className="inline-block mb-8">
          <LogoFull width={170} />
        </Link>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Masuk ke Dashboard</h1>
        <p className="text-sm text-zinc-400 mt-2">Selamat datang kembali. Pilih akun label, artist, atau admin Anda.</p>

        <form onSubmit={submit} className="mt-7 space-y-4">
          <div>
            <label className="rm-label">Email</label>
            <input
              data-testid={LOGIN.emailInput}
              type="email"
              className="rm-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="email@label.com"
              required
            />
          </div>
          <div>
            <label className="rm-label">Password</label>
            <input
              data-testid={LOGIN.passwordInput}
              type="password"
              className="rm-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {err && <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-xl px-3 py-2">{err}</div>}
          <button data-testid={LOGIN.submitButton} type="submit" className="rm-btn-primary w-full" disabled={loading}>
            {loading ? "Memproses…" : "Masuk"}
          </button>
        </form>
        <div className="mt-5 flex justify-between text-sm">
          <Link to="/forgot-password" data-testid={LOGIN.forgotPasswordLink} className="text-zinc-400 hover:text-white">Lupa password?</Link>
          <Link to="/register" data-testid={LOGIN.registerLink} className="font-semibold rm-gradient-text">Daftar →</Link>
        </div>
      </div>
    </div>
  );
}
