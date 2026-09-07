import React from "react";
import { Check, Lock, Loader2 } from "lucide-react";

export const KycStepsGuide = ({ kyc }) => {
  const prereq = !!kyc?.prerequisites_complete;
  const hasDoc = !!kyc?.document;
  const verified = kyc?.status === "verified";
  const pending = kyc?.status === "pending_review";

  const missingLabels = (kyc?.checks || []).filter((c) => !c.complete).map((c) => c.label);

  const steps = [
    {
      n: 1,
      title: "Lengkapi data profil, logo, kontrak & rekening",
      done: prereq,
      locked: false,
      detail: !prereq && missingLabels.length ? `Masih perlu: ${missingLabels.join(", ")}` : "Semua data profil sudah lengkap.",
    },
    {
      n: 2,
      title: "Unggah foto KTP penanggung jawab",
      done: hasDoc,
      locked: !prereq,
      detail: !prereq ? "Terbuka setelah data profil lengkap." : hasDoc ? "KTP sudah diunggah." : "Tombol unggah KTP kini bisa ditekan di bawah.",
    },
    {
      n: 3,
      title: "Verifikasi oleh admin",
      done: verified,
      locked: !hasDoc,
      detail: verified ? "Akun Anda sudah terverifikasi." : pending ? "Sedang direview tim kami." : "Menunggu KTP diunggah.",
    },
  ];
  const activeIndex = steps.findIndex((s) => !s.done && !s.locked);

  return (
    <section className="rounded-lg border border-white/10 bg-white/[0.02] p-5" data-testid="kyc-steps-guide">
      <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Langkah Verifikasi Akun</div>
      <p className="mt-1 text-sm text-zinc-400">Ikuti urutan berikut sampai akun Anda terverifikasi.</p>
      <ol className="mt-4 space-y-3">
        {steps.map((step, index) => {
          const active = index === activeIndex;
          return (
            <li key={step.n} className={`flex items-start gap-3 rounded-lg border p-3 transition-colors ${active ? "border-[#FF1F8E]/40 bg-[rgba(255,31,142,0.06)]" : "border-transparent"}`} data-testid={`kyc-step-${step.n}`}>
              <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold ${step.done ? "bg-emerald-400/15 text-emerald-300" : step.locked ? "bg-white/[0.04] text-zinc-600" : "bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white"}`}>
                {step.done ? <Check className="h-4 w-4" /> : step.locked ? <Lock className="h-3.5 w-3.5" /> : (active && pending && step.n === 3 ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : step.n)}
              </span>
              <div className="min-w-0">
                <div className={`text-sm font-semibold ${step.done ? "text-zinc-300" : step.locked ? "text-zinc-500" : "text-white"}`}>{step.title}</div>
                <div className="mt-0.5 text-xs text-zinc-500">{step.detail}</div>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
};
