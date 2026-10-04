import axios from "axios";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
const IS_BROWSER = typeof window !== "undefined";
// Every deployed frontend is served by the same ingress as `/api`. Always use
// a relative browser URL so apex/www aliases cannot turn auth into cross-origin.
export const API_BASE = IS_BROWSER ? "/api" : `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Stage large files directly in the existing private R2 bucket. Finalization
// returns the existing upload route's response, including all its validation.
api.interceptors.request.use(async (config) => {
  if (typeof FormData === "undefined" || !(config.data instanceof FormData)) return config;
  const entries = Array.from(config.data.entries());
  const files = entries.filter(([, value]) => typeof Blob !== "undefined" && value instanceof Blob);
  if (files.length !== 1 || files[0][0] !== "file" || files[0][1].size <= 3 * 1024 * 1024) return config;
  const file = files[0][1];
  const fields = Object.fromEntries(entries.filter(([name]) => name !== "file"));
  const initiated = await api.post("/uploads/initiate", {
    target: config.url, filename: file.name || "upload", content_type: file.type || "application/octet-stream",
    size: file.size, fields, query: config.params || {},
  }, { signal: config.signal });
  await axios.put(initiated.data.url, file, {
    headers: { "Content-Type": initiated.data.content_type }, withCredentials: false,
    signal: config.signal, onUploadProgress: config.onUploadProgress,
  });
  config.url = "/uploads/finalize";
  config.data = { upload_id: initiated.data.upload_id };
  config.params = undefined;
  config.headers.set("Content-Type", "application/json");
  config.timeout = Math.max(config.timeout || 0, 240000);
  return config;
});

// Intercept 401: try refresh once
let isRefreshing = false;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retry && !original.url?.includes("/auth/")) {
      original._retry = true;
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          await api.post("/auth/refresh");
          isRefreshing = false;
          return api(original);
        } catch (_e) {
          isRefreshing = false;
        }
      }
    }
    return Promise.reject(err);
  }
);

export function formatApiError(detail) {
  if (detail == null) return "Terjadi kesalahan. Coba lagi.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  if (detail && typeof detail.message === "string") return detail.message;
  return String(detail);
}

export function fileUrl(path) {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return IS_BROWSER ? path : `${BACKEND_URL}${path}`;
}
