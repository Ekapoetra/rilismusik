import React, { useEffect, useState } from "react";
import { fileUrl } from "@/api/client";

export const LabelLogo = ({ src, labelName, className = "h-12 w-12", testId }) => {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [src]);
  const initial = (labelName || "L").trim().charAt(0).toUpperCase() || "L";

  return (
    <div className={`${className} grid shrink-0 place-items-center overflow-hidden rounded-lg border border-white/10 bg-white/[0.05]`} data-testid={testId}>
      {src && !failed ? (
        <img src={fileUrl(src)} alt={`Logo ${labelName || "label"}`} className="h-full w-full object-contain p-1" onError={() => setFailed(true)} data-testid={`${testId}-image`} />
      ) : (
        <span className="font-display text-lg font-black text-zinc-300" aria-label={`Inisial ${labelName || "label"}`} data-testid={`${testId}-fallback`}>{initial}</span>
      )}
    </div>
  );
};