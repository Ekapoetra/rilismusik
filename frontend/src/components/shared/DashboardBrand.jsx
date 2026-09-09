import React from "react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

export const DashboardBrand = ({ compact = false, testId = "dashboard-brand" }) => {
  const { theme } = useAppPreferences();
  return <div className="dashboard-brand" data-testid={testId} translate="no"><img src={`/brand/logo-ui-${theme}.png`} alt="Rilis Musik" data-testid={`${testId}-logo`} />{!compact && <strong>RILIS MUSIK</strong>}</div>;
};