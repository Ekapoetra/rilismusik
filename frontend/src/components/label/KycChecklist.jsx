import React from "react";
import { Check, CircleDashed } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export const KycChecklist = ({ kyc }) => {
  const percentage = kyc?.total ? Math.round((kyc.completed / kyc.total) * 100) : 0;
  return (
    <section className="border-y border-white/10 py-5" data-testid="kyc-checklist">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Kelengkapan</div>
          <div className="mt-1 font-display text-lg font-bold" data-testid="kyc-checklist-progress-text">
            {kyc?.completed || 0} dari {kyc?.total || 0} persyaratan
          </div>
        </div>
        <div className="font-mono text-sm text-zinc-400" data-testid="kyc-checklist-percentage">{percentage}%</div>
      </div>
      <Progress value={percentage} className="mt-4 bg-white/10 [&>div]:bg-emerald-400" data-testid="kyc-checklist-progress" />
      <div className="mt-5 grid gap-x-8 gap-y-3 md:grid-cols-2">
        {(kyc?.checks || []).map((item) => (
          <div className="flex items-center gap-3 text-sm" key={item.key} data-testid={`kyc-check-${item.key}`}>
            <span className={`grid h-6 w-6 shrink-0 place-items-center rounded-md border ${item.complete ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300" : "border-white/10 bg-white/[0.03] text-zinc-600"}`}>
              {item.complete ? <Check className="h-3.5 w-3.5" /> : <CircleDashed className="h-3.5 w-3.5" />}
            </span>
            <span className={item.complete ? "text-zinc-200" : "text-zinc-500"}>{item.label}</span>
          </div>
        ))}
        <div className="flex items-center gap-3 text-sm" data-testid="kyc-check-ktp">
          <span className={`grid h-6 w-6 shrink-0 place-items-center rounded-md border ${kyc?.document ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300" : "border-white/10 bg-white/[0.03] text-zinc-600"}`}>
            {kyc?.document ? <Check className="h-3.5 w-3.5" /> : <CircleDashed className="h-3.5 w-3.5" />}
          </span>
          <span className={kyc?.document ? "text-zinc-200" : "text-zinc-500"}>Foto KTP Penanggung Jawab</span>
        </div>
      </div>
    </section>
  );
};