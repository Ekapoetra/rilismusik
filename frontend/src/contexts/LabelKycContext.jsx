import React, { createContext, useContext, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/api/AuthContext";
import { sharedRead } from "@/api/sharedRead";

const LabelKycContext = createContext(null);
export function LabelKycProvider({ children }) {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const scope = JSON.stringify([user?.id, user?.active_label_id]);
  const [state, setState] = useState({ scope: null, kyc: null, loading: true, error: false });
  useEffect(() => {
    let active = true;
    setState((value) => ({ scope, kyc: value.scope === scope ? value.kyc : null, loading: true, error: false }));
    sharedRead(scope, "/label/kyc")
      .then(({ data }) => { if (active) setState({ scope, kyc: data, loading: false, error: false }); })
      .catch(() => { if (active) setState({ scope, kyc: null, loading: false, error: true }); });
    return () => { active = false; };
  }, [scope, pathname]);
  useEffect(() => {
    const update = (event) => setState({ scope, kyc: event.detail, loading: false, error: false });
    window.addEventListener("rilismusik:kyc-updated", update);
    return () => window.removeEventListener("rilismusik:kyc-updated", update);
  }, [scope]);
  return <LabelKycContext.Provider value={state.scope === scope ? state : { kyc: null, loading: true, error: false }}>{children}</LabelKycContext.Provider>;
}
export function useLabelKyc() { return useContext(LabelKycContext); }
