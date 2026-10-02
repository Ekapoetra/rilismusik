import React, { createContext, useContext, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/api/AuthContext";
import { sharedRead } from "@/api/sharedRead";

const LabelKycContext = createContext(null);
export function LabelKycProvider({ children }) {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [state, setState] = useState({ kyc: null, loading: true, error: false });
  useEffect(() => {
    let active = true;
    setState((value) => ({ ...value, loading: true, error: false }));
    sharedRead(user?.id, "/label/kyc")
      .then(({ data }) => { if (active) setState({ kyc: data, loading: false, error: false }); })
      .catch(() => { if (active) setState({ kyc: null, loading: false, error: true }); });
    return () => { active = false; };
  }, [user?.id, pathname]);
  useEffect(() => {
    const update = (event) => setState({ kyc: event.detail, loading: false, error: false });
    window.addEventListener("rilismusik:kyc-updated", update);
    return () => window.removeEventListener("rilismusik:kyc-updated", update);
  }, []);
  return <LabelKycContext.Provider value={state}>{children}</LabelKycContext.Provider>;
}
export function useLabelKyc() { return useContext(LabelKycContext); }
