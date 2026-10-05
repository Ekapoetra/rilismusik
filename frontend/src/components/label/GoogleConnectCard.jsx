import React from "react";
import { CheckCircle2, Link2 } from "lucide-react";
import { useAuth } from "@/api/AuthContext";
import { GoogleAuthButton } from "@/components/auth/GoogleAuthButton";

const fmtDate = (value) => {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
};

// Google is only an extra sign-in method. Linking it never changes the
// account's verification status (Verifikasi Akun / email).
export function GoogleConnectCard() {
  const { user, refresh } = useAuth();
  const connected = Boolean(user?.google_subject);
  const linkedOn = fmtDate(user?.google_linked_at);
  return (
    <section className="rm-card p-5" data-testid="label-google-connect">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0 space-y-1">
          <h2 className="flex items-center gap-2 font-display text-lg font-bold">
            {connected ? <CheckCircle2 className="h-5 w-5 text-emerald-400" /> : <Link2 className="h-5 w-5 text-sky-300" />}
            {connected ? "Google Terhubung" : "Hubungkan ke Google"}
          </h2>
          {connected ? (
            <p className="text-sm text-emerald-300" data-testid="label-google-connected">
              Anda bisa masuk dengan Google{user?.google_email ? <> sebagai <span className="font-semibold" translate="no">{user.google_email}</span></> : null}{linkedOn ? ` · terhubung sejak ${linkedOn}` : ""}.
            </p>
          ) : (
            <p className="text-sm text-zinc-400" data-testid="label-google-not-connected">
              Masuk tanpa mengetik password. Pilih akun Google dengan email yang sama seperti akun label Anda (<span translate="no">{user?.email}</span>).
            </p>
          )}
          <p className="text-xs text-zinc-500">Menghubungkan Google tidak mengubah status verifikasi akun Anda.</p>
        </div>
        {!connected && (
          <div className="w-full shrink-0 md:w-80">
            <GoogleAuthButton source="profile" mode="link" onLinked={refresh} />
          </div>
        )}
      </div>
    </section>
  );
}
