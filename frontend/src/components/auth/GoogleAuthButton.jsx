import React from "react";

export const GoogleAuthButton = ({ source }) => {
  const startGoogleAuth = () => {
    const authUrl = process.env.REACT_APP_GOOGLE_AUTH_URL;
    if (!authUrl) throw new Error("REACT_APP_GOOGLE_AUTH_URL belum dikonfigurasi");
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/label/dashboard";
    window.location.href = `${authUrl.replace(/\/$/, "")}/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return <button type="button" onClick={startGoogleAuth} className="rm-btn-ghost flex w-full items-center justify-center gap-3 border-white/15 bg-white text-zinc-900 hover:bg-zinc-100" data-testid={`${source}-google-auth-button`}>
    <span className="grid h-5 w-5 place-items-center rounded-full bg-white font-sans text-base font-bold text-[#4285F4]" aria-hidden="true">G</span>
    Lanjutkan dengan Google
  </button>;
};