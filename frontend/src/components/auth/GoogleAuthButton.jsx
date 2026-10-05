import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { loadGoogleIdentity } from "@/lib/googleIdentity";

export const GoogleAuthButton = ({ source, mode = "login", onLinked }) => {
  const clientId = (process.env.REACT_APP_GOOGLE_CLIENT_ID || "").trim();
  const { loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const target = useRef(null);
  const nonceRequest = useRef(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [linked, setLinked] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!clientId || linked) return undefined;
    let active = true;
    let inFlight = false;
    setReady(false); setError("");
    const element = target.current;
    // StrictMode may mount an effect twice. Reuse its challenge request so a
    // late first response cannot overwrite the cookie used by the active SDK.
    if (!nonceRequest.current || nonceRequest.current.attempt !== attempt) {
      nonceRequest.current = { attempt, promise: api.get("/auth/google/nonce") };
    }
    Promise.all([loadGoogleIdentity(), nonceRequest.current.promise])
      .then(([identity, response]) => {
        if (!active) return;
        identity.initialize({
          client_id: clientId, nonce: response.data.nonce,
          auto_select: false, ux_mode: "popup",
          callback: async ({ credential }) => {
            if (!active || inFlight || !credential) return;
            inFlight = true; setBusy(true); setError("");
            try {
              if (mode === "link") {
                await api.post("/auth/google/link", { credential });
                if (active) { setLinked(true); onLinked?.(); }
              } else {
                await loginWithGoogle(credential);
                if (active) navigate("/label/dashboard", { replace: true });
              }
            } catch (err) {
              if (active) setError(formatApiError(err.response?.data?.detail || err.message));
            } finally {
              inFlight = false;
              if (active) setBusy(false);
            }
          },
        });
        element.replaceChildren();
        identity.renderButton(element, {
          type: "standard", theme: "outline", size: "large", text: "continue_with",
          shape: "pill", logo_alignment: "left", locale: "id",
          width: Math.min(400, Math.max(200, Math.floor(element.getBoundingClientRect().width || 320))),
        });
        setReady(true);
      })
      .catch((err) => { if (active) setError(formatApiError(err.response?.data?.detail || err.message)); });
    return () => { active = false; element?.replaceChildren(); };
  }, [clientId, attempt, loginWithGoogle, navigate, mode, onLinked, linked]);

  if (!clientId) return <p className="text-center text-xs text-zinc-500">{mode === "link" ? "Hubungkan Google belum tersedia saat ini." : "Login Google belum tersedia. Gunakan email dan password."}</p>;
  if (linked) return <p role="status" className="text-sm text-emerald-300">Akun Google berhasil dihubungkan.</p>;
  return <div className="space-y-2" data-testid={`${source}-google-auth-button`}>
    <div ref={target} className={`flex min-h-[40px] w-full justify-center ${busy ? "pointer-events-none opacity-60" : ""}`} aria-busy={busy} />
    {(!ready || busy) && !error && <p role="status" className="text-center text-xs text-zinc-400">{busy ? "Memverifikasi akun Google…" : "Memuat Google…"}</p>}
    {error && <div role="alert" className="text-center text-xs text-red-300"><p>{error}</p><button type="button" onClick={() => setAttempt((value) => value + 1)} className="mt-2 underline">Muat ulang tombol Google</button></div>}
  </div>;
};
