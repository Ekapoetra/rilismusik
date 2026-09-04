import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/api/AuthContext";

const ADMIN_FALLBACKS = [
  ["dashboard.view", "/admin/dashboard"], ["analytics.view", "/admin/analytics"],
  ["labels.view", "/admin/labels"], ["kyc.view", "/admin/kyc"],
  ["artists.view", "/admin/artists"], ["releases.view", "/admin/releases"],
  ["payments.view", "/admin/payments"], ["royalty.view", "/admin/royalty"],
  ["withdraw.view", "/admin/withdraw"], ["support.view", "/admin/tickets"],
  ["ui.settings.view", "/admin/ui-settings"], ["access.roles.view", "/admin/access"],
];

const adminFallback = (user) => user?.role === "super_admin" ? "/admin/dashboard" : ADMIN_FALLBACKS.find(([permission]) => (user?.permissions || []).includes(permission))?.[1] || "/";

export default function ProtectedRoute({ children, roles, permission }) {
  const { user, loading, hasPermission, isAdmin } = useAuth();
  const loc = useLocation();

  if (loading || user === null) {
    return (
      <div className="min-h-screen grid place-items-center">
        <div className="rm-glass rounded-3xl px-6 py-4 text-sm text-slate-500">Memuat…</div>
      </div>
    );
  }
  if (user === false) {
    return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  }
  if (roles && roles.length && !roles.includes(user.role)) {
    // Redirect to correct dashboard based on role
    if (user.role === "label") return <Navigate to="/label/dashboard" replace />;
    if (user.role === "artist") return <Navigate to="/artist/dashboard" replace />;
    if (isAdmin)
      return <Navigate to={adminFallback(user)} replace />;
    return <Navigate to="/" replace />;
  }
  if (permission && !hasPermission(permission)) {
    return <Navigate to={isAdmin ? adminFallback(user) : "/"} replace />;
  }
  return children;
}
