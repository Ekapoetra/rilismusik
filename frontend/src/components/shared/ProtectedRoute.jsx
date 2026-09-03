import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/api/AuthContext";

export default function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();
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
    if (["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content", "admin_marketing"].includes(user.role))
      return <Navigate to="/admin/dashboard" replace />;
    return <Navigate to="/" replace />;
  }
  return children;
}
