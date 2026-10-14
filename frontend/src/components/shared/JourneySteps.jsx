import React from "react";
import { Check, XOctagon } from "lucide-react";

// Horizontal position journey (SugarCRM-style, dark theme): the current stage
// glows pink, completed stages show a check, upcoming stages stay dimmed.
// `terminal` replaces the last node with a red end-state (e.g. "Ditolak").
export default function JourneySteps({ steps, current = 0, terminal = null, testPrefix = "journey" }) {
  const isTerminal = Boolean(terminal);
  return (
    <div className="flex items-start" data-testid={`${testPrefix}-journey`}>
      {steps.map((s, i) => {
        const isLast = i === steps.length - 1;
        const terminalHere = isTerminal && isLast;
        const state = terminalHere ? "terminal" : (isTerminal || i < current) ? "done" : i === current ? "current" : "upcoming";
        const Icon = terminalHere ? XOctagon : state === "done" ? Check : s.icon;
        const nodeCls = {
          terminal: "border-red-400/50 bg-red-400/10 text-red-300",
          done: "border-[#FF1F8E]/40 bg-[#FF1F8E]/10 text-pink-300",
          current: "border-pink-300 bg-[#FF1F8E]/20 text-pink-200 shadow-[0_0_14px_rgba(255,31,142,0.25)]",
          upcoming: "border-white/10 bg-white/[0.02] text-zinc-600",
        }[state];
        const label = terminalHere ? terminal : s.label;
        return (
          <React.Fragment key={s.key}>
            <div className="flex w-16 flex-none flex-col items-center text-center" data-testid={`${testPrefix}-step-${s.key}`} data-state={state}>
              <div className={`grid h-10 w-10 place-items-center rounded-full border transition-colors ${nodeCls}`}>
                <Icon className="h-4 w-4" />
              </div>
              <div className={`mt-2 whitespace-nowrap text-[10px] font-bold uppercase tracking-widest ${state === "upcoming" ? "text-zinc-600" : state === "terminal" ? "text-red-300" : "text-zinc-300"}`}>
                {label}
              </div>
              {state === "current" && <div className="mt-0.5 text-[9px] font-bold uppercase tracking-widest text-pink-300" data-testid={`${testPrefix}-here`}>di sini</div>}
            </div>
            {!isLast && (
              <div
                className={`mt-5 h-px min-w-3 flex-1 ${
                  state === "upcoming" ? "bg-white/10"
                    : isTerminal && i + 1 === steps.length - 1 ? "bg-gradient-to-r from-[#FF1F8E]/40 to-red-400/50"
                    : "bg-[#FF1F8E]/40"
                }`}
                data-testid={`${testPrefix}-line-${i}`}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
