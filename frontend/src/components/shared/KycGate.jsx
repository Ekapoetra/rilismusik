import React from "react";
import { Link } from "react-router-dom";
import { Clock3, LockKeyhole, ShieldAlert } from "lucide-react";

export const KycGate = ({ status, loading }) => {
  const pending = status === "pending_review";
  const rejected = status === "rejected";
  const Icon = pending ? Clock3 : rejected ? ShieldAlert : LockKeyhole;
  return (
    <div className="absolute inset-0 z-20 flex items-start justify-center px-4 pt-24 md:pt-32" data-testid="label-kyc-lock-overlay">
      <div className="w-full max-w-lg rounded-lg border border-white/10 bg-[#0F0F0F]/95 p-7 shadow-2xl backdrop-blur-xl rm-fade-up" role="dialog" aria-modal="true" data-testid="label-kyc-lock-dialog">
        <Icon className={`h-7 w-7 ${rejected ? "text-red-300" : pending ? "text-amber-300" : "text-zinc-200"}`} />
        <div className="mt-5 text-xs font-bold uppercase tracking-widest text-zinc-500">Fitur terkunci</div>
        <h2 className="mt-2 font-display text-2xl font-extrabold" data-testid="label-kyc-lock-title">{loading ? "Memeriksa aktivasi akun" : pending ? "Verifikasi Akun sedang direview" : rejected ? "Verifikasi Akun perlu diperbaiki" : "Selesaikan Verifikasi Akun"}</h2>
        <p className="mt-3 text-sm leading-relaxed text-zinc-400" data-testid="label-kyc-lock-message">{pending ? "Tim kami sedang memeriksa identitas Anda. Status dan dokumen dapat dipantau dari halaman Profil." : rejected ? "Lihat alasan penolakan, perbaiki data, lalu unggah ulang KTP dari halaman Profil." : "Lengkapi data label, kontrak, rekening, logo, dan KTP agar fitur ini dapat digunakan."}</p>
        {!loading && <Link to="/label/profile" className="rm-btn-primary mt-6 inline-flex items-center justify-center" data-testid="label-kyc-lock-profile-link">Buka Profil & Verifikasi</Link>}
      </div>
    </div>
  );
};