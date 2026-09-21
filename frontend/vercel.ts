const rawBackendOrigin = process.env.EMERGENT_BACKEND_URL || "";
const backendOrigin = rawBackendOrigin.trim().replace(/\/+$/, "");

if (!backendOrigin) {
  throw new Error(
    "EMERGENT_BACKEND_URL is required. Set it in Vercel Project Settings → Environment Variables " +
    "to the public Emergent backend origin, without /api (example: https://your-backend.example.com)."
  );
}

if (!/^https:\/\//i.test(backendOrigin)) {
  throw new Error("EMERGENT_BACKEND_URL must start with https://");
}

const noApiCacheHeaders = [
  { key: "x-vercel-enable-rewrite-caching", value: "0" },
  { key: "Cache-Control", value: "no-store, private" },
];

export const config = {
  framework: "create-react-app",
  buildCommand: "yarn build",
  outputDirectory: "build",
  trailingSlash: false,

  // Keep API calls same-origin in the browser. This preserves the existing
  // HttpOnly cookie auth model while the real FastAPI backend remains on Emergent.
  rewrites: [
    { source: "/api", destination: `${backendOrigin}/api` },
    { source: "/api/:path*", destination: `${backendOrigin}/api/:path*` },

    // React Router SPA fallback. API rewrites must stay above this rule.
    { source: "/(.*)", destination: "/index.html" },
  ],

  // Authenticated API responses must never be cached at the Vercel edge.
  headers: [
    { source: "/api", headers: noApiCacheHeaders },
    { source: "/api/:path*", headers: noApiCacheHeaders },
  ],
};
