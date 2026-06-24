import React from "react";
import { Construction } from "lucide-react";

export default function ComingSoon({ title, description }) {
  return (
    <div className="max-w-3xl">
      <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">{title}</div>
      <h1 className="font-display text-3xl font-extrabold tracking-tighter mb-2">{title}</h1>
      <div className="rm-card p-10 text-center">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-amber-50 text-amber-600 grid place-items-center mb-4">
          <Construction className="w-7 h-7" />
        </div>
        <div className="font-display font-bold text-xl tracking-tight">Sedang dikembangkan</div>
        <p className="text-sm text-slate-600 mt-2 max-w-md mx-auto">{description}</p>
      </div>
    </div>
  );
}
