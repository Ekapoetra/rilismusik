// Google's SDK renders the official button, including its current Google logo.
const SCRIPT_URL = "https://accounts.google.com/gsi/client";
let scriptPromise;

export function loadGoogleIdentity() {
  if (window.google?.accounts?.id) return Promise.resolve(window.google.accounts.id);
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_URL;
    script.async = true;
    script.defer = true;
    const timeout = setTimeout(() => fail(), 15000);
    function fail() {
      clearTimeout(timeout);
      script.remove();
      scriptPromise = undefined;
      reject(new Error("Google belum dapat dimuat. Coba lagi atau gunakan email dan password."));
    }
    script.onerror = fail;
    script.onload = () => {
      clearTimeout(timeout);
      const identity = window.google?.accounts?.id;
      if (identity) resolve(identity);
      else fail();
    };
    document.head.appendChild(script);
  });
  return scriptPromise;
}
