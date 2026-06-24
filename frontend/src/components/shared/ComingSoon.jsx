import React from "react";
import { Construction } from "lucide-react";

export default function ComingSoon({ title, description }) {
  return (
    <div className="max-w-3xl">
      <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">{title}</div>
      <h1 className="font-display text-3xl font-extrabold tracking-tighter mb-2 text-white">{title}</h1>
      <div className="rm-card p-10 text-center">
        <div className="w-14 h-14 mx-auto rounded-2xl grid place-items-center mb-4" style={{ background: "linear-gradient(135deg, rgba(255,31,142,0.15), rgba(162,78,255,0.15))", color: "#FF8AC0" }}>
          <Construction className="w-7 h-7" />
        </div>
        <div className="font-display font-bold text-xl tracking-tight text-white">Sedang dikembangkan</div>
        <p className="text-sm text-zinc-400 mt-2 max-w-md mx-auto">{description}</p>
      </div>
    </div>
  );
}
