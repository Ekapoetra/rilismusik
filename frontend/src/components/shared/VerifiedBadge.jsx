import React from "react";

// Label verification seal (owner reference): flat 11-point star with slightly
// rounded tips. The check is cut out of the shape (fill-rule evenodd), so it is
// transparent and shows whatever background sits behind the badge — no stroke.
// Same path as the prototype's SEAL_PATH9 so both surfaces read alike.
export const SEAL_PATH = "M11.63 0.75Q12 0.5 12.37 0.75L14.59 2.25Q14.82 2.4 15.09 2.39L17.77 2.34Q18.22 2.33 18.4 2.74L19.45 5.2Q19.56 5.45 19.79 5.59L22.08 6.99Q22.46 7.22 22.39 7.67L21.95 10.31Q21.9 10.58 22.02 10.82L23.19 13.23Q23.38 13.64 23.08 13.97L21.28 15.96Q21.1 16.16 21.07 16.42L20.75 19.08Q20.69 19.53 20.26 19.65L17.67 20.35Q17.41 20.42 17.24 20.62L15.53 22.69Q15.24 23.03 14.81 22.9L12.26 22.09Q12 22.01 11.74 22.09L9.19 22.9Q8.76 23.03 8.47 22.69L6.76 20.62Q6.59 20.42 6.33 20.35L3.74 19.65Q3.31 19.53 3.25 19.08L2.93 16.42Q2.9 16.16 2.72 15.96L0.92 13.97Q0.62 13.64 0.81 13.23L1.98 10.82Q2.1 10.58 2.05 10.31L1.61 7.67Q1.54 7.22 1.92 6.99L4.21 5.59Q4.44 5.45 4.55 5.2L5.6 2.74Q5.78 2.33 6.23 2.34L8.91 2.39Q9.18 2.4 9.41 2.25Z M7.94 12.33L10.55 14.06L15.17 9.11L16.34 10.33L10.89 16.78L7.11 13.72Z";

export const VerifiedBadge = ({ className = "h-4 w-4", title = "Terverifikasi", testid = "verified-badge" }) => (
  <svg viewBox="0 0 24 24" className={`shrink-0 ${className}`} role="img" aria-label={title} data-testid={testid}>
    <title>{title}</title>
    <path fill="#2d96e9" fillRule="evenodd" d={SEAL_PATH} />
  </svg>
);
