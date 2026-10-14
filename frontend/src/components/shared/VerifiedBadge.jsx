import React from "react";

// Instagram/Meta-style verification seal: two rounded squares (superellipse,
// n=4) rotated 45° and merged — eight soft points around a white check.
// Same shape as the prototype's SEAL_PATH9 so both surfaces read alike.
export const SEAL_PATH = "M23.4 12.0L23.3 12.7L23.1 13.4L22.8 14.1L22.4 14.7L21.9 15.3L21.6 15.9L21.4 16.6L21.3 17.3L21.1 18.1L20.9 18.8L20.5 19.4L20.0 20.0L19.4 20.5L18.8 20.9L18.1 21.1L17.3 21.3L16.6 21.4L15.9 21.6L15.3 21.9L14.7 22.4L14.1 22.8L13.4 23.1L12.7 23.3L12.0 23.4L11.2 23.3L10.5 23.1L9.8 22.8L9.2 22.4L8.6 21.9L8.0 21.6L7.3 21.4L6.6 21.3L5.8 21.1L5.1 20.9L4.5 20.5L3.9 20.0L3.4 19.4L3.1 18.8L2.8 18.1L2.6 17.3L2.5 16.6L2.3 15.9L2.0 15.3L1.5 14.7L1.1 14.1L0.8 13.4L0.6 12.7L0.6 12.0L0.6 11.2L0.8 10.5L1.1 9.8L1.5 9.2L2.0 8.6L2.3 8.0L2.5 7.3L2.6 6.6L2.8 5.8L3.1 5.1L3.4 4.5L3.9 3.9L4.5 3.4L5.1 3.1L5.8 2.8L6.6 2.6L7.3 2.5L8.0 2.3L8.6 2.0L9.2 1.5L9.8 1.1L10.5 0.8L11.2 0.6L12.0 0.6L12.7 0.6L13.4 0.8L14.1 1.1L14.7 1.5L15.3 2.0L15.9 2.3L16.6 2.5L17.3 2.6L18.1 2.8L18.8 3.1L19.4 3.4L20.0 3.9L20.5 4.5L20.9 5.1L21.1 5.8L21.3 6.6L21.4 7.3L21.6 8.0L21.9 8.6L22.4 9.2L22.8 9.8L23.1 10.5L23.3 11.2Z";

export const VerifiedBadge = ({ className = "h-4 w-4", title = "Terverifikasi", testid = "verified-badge" }) => (
  <svg viewBox="0 0 24 24" className={`shrink-0 ${className}`} role="img" aria-label={title} data-testid={testid}>
    <title>{title}</title>
    <path fill="#0095f6" d={SEAL_PATH} />
    <path d="M7.7 12.5l2.9 2.9 5.7-6.2" fill="none" stroke="#fff" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
