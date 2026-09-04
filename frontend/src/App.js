import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider } from "@/api/AuthContext";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import LabelLayout from "@/components/shared/LabelLayout";
import AdminLayout from "@/components/shared/AdminLayout";

import Landing from "@/pages/Landing";
import Login from "@/pages/auth/Login";
import Register from "@/pages/auth/Register";
import ForgotPassword from "@/pages/auth/ForgotPassword";
import ResetPassword from "@/pages/auth/ResetPassword";
import GoogleAuthCallback from "@/pages/auth/GoogleAuthCallback";

import LabelDashboard from "@/pages/label/Dashboard";
import LabelReleases from "@/pages/label/Releases";
import UploadRelease from "@/pages/label/UploadRelease";
import ReleaseDetail from "@/pages/label/ReleaseDetail";
import LabelArtists from "@/pages/label/Artists";
import LabelProfile from "@/pages/label/Profile";
import LabelInvoices from "@/pages/label/Invoices";
import LabelRoyalty from "@/pages/label/Royalty";
import LabelWithdraw from "@/pages/label/Withdraw";
import LabelSupportTickets from "@/pages/label/SupportTickets";
import LabelSupportTicketDetail from "@/pages/label/SupportTicketDetail";
import LabelContract from "@/pages/label/Contract";
import LabelWami from "@/pages/label/Wami";

import AdminDashboard from "@/pages/admin/Dashboard";
import AdminAnalytics from "@/pages/admin/Analytics";
import AdminLabels from "@/pages/admin/Labels";
import LabelRateImport from "@/pages/admin/LabelRateImport";
import AdminLabelDetail from "@/pages/admin/LabelDetail";
import AdminReleases from "@/pages/admin/Releases";
import AdminReleaseDetail from "@/pages/admin/ReleaseDetail";
import AdminArtists from "@/pages/admin/Artists";
import AdminPayments from "@/pages/admin/Payments";
import AdminCMS from "@/pages/admin/CMS";
import AdminUsers from "@/pages/admin/AdminUsers";
import AdminActivityLogs from "@/pages/admin/ActivityLogs";
import AdminRoyaltyImport from "@/pages/admin/RoyaltyImport";
import AdminRoyaltyDetail from "@/pages/admin/RoyaltyDetail";
import AdminWithdraw from "@/pages/admin/Withdraw";
import AdminTickets from "@/pages/admin/Tickets";
import AdminTicketDetail from "@/pages/admin/TicketDetail";
import AdminContracts from "@/pages/admin/Contracts";
import AdminWami from "@/pages/admin/Wami";
import AdminMigrate from "@/pages/admin/Migrate";
import AdminKycReviews from "@/pages/admin/KycReviews";
import AdminAccessControl from "@/pages/admin/AccessControl";
import AdminUiSettings from "@/pages/admin/UiSettings";
import AdminNotifications from "@/pages/admin/Notifications";
import { Toaster } from "@/components/ui/sonner";

import ArtistDashboard from "@/pages/artist/Dashboard";

const LABEL_ROLES = ["label"];
const ARTIST_ROLES = ["artist"];
const ADMIN_ROLES = ["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content", "admin_marketing", "admin_ui", "admin_custom"];
const guard = (permission, element) => <ProtectedRoute permission={permission}>{element}</ProtectedRoute>;

function AppRoutes() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <GoogleAuthCallback />;
  return (
    <Routes>
          {/* Public */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />

          {/* Label */}
          <Route element={<ProtectedRoute roles={LABEL_ROLES}><LabelLayout /></ProtectedRoute>}>
            <Route path="/label/dashboard" element={<LabelDashboard />} />
            <Route path="/label/releases" element={<LabelReleases />} />
            <Route path="/label/releases/upload" element={<UploadRelease />} />
            <Route path="/label/releases/:id" element={<ReleaseDetail />} />
            <Route path="/label/releases/:id/edit" element={<UploadRelease />} />
            <Route path="/label/artists" element={<LabelArtists />} />
            <Route path="/label/profile" element={<LabelProfile />} />
            <Route path="/label/invoices" element={<LabelInvoices />} />
            <Route path="/label/royalty" element={<LabelRoyalty />} />
            <Route path="/label/withdraw" element={<LabelWithdraw />} />
            <Route path="/label/support" element={<LabelSupportTickets />} />
            <Route path="/label/support/:id" element={<LabelSupportTicketDetail />} />
            <Route path="/label/contract" element={<LabelContract />} />
            <Route path="/label/wami" element={<LabelWami />} />
          </Route>

          {/* Artist */}
          <Route element={<ProtectedRoute roles={ARTIST_ROLES}><ArtistDashboard /></ProtectedRoute>} path="/artist/dashboard" />

          {/* Admin */}
          <Route element={<ProtectedRoute roles={ADMIN_ROLES}><AdminLayout /></ProtectedRoute>}>
            <Route path="/admin/dashboard" element={guard("dashboard.view", <AdminDashboard />)} />
            <Route
              path="/admin/analytics"
              element={
                guard("analytics.view", <AdminAnalytics />)
              }
            />
            <Route path="/admin/labels" element={guard("labels.view", <AdminLabels />)} />
            <Route path="/admin/labels/rate-import" element={guard("royalty.import", <LabelRateImport />)} />
            <Route path="/admin/labels/:id" element={guard("labels.view", <AdminLabelDetail />)} />
            <Route path="/admin/kyc" element={guard("kyc.view", <AdminKycReviews />)} />
            <Route path="/admin/artists" element={guard("artists.view", <AdminArtists />)} />
            <Route path="/admin/releases" element={guard("releases.view", <AdminReleases />)} />
            <Route path="/admin/releases/:id" element={guard("releases.view", <AdminReleaseDetail />)} />
            <Route path="/admin/payments" element={guard("payments.view", <AdminPayments />)} />
            <Route path="/admin/cms" element={guard("cms.view", <AdminCMS />)} />
            <Route path="/admin/admin-users" element={guard("access.users.view", <AdminUsers />)} />
            <Route path="/admin/access" element={guard("access.roles.view", <AdminAccessControl />)} />
            <Route path="/admin/ui-settings" element={guard("ui.settings.view", <AdminUiSettings />)} />
            <Route path="/admin/notifications" element={guard("notifications.view", <AdminNotifications />)} />
            <Route path="/admin/activity-logs" element={guard("activity.view", <AdminActivityLogs />)} />
            <Route path="/admin/royalty" element={guard("royalty.view", <AdminRoyaltyImport />)} />
            <Route path="/admin/royalty/:id" element={guard("royalty.view", <AdminRoyaltyDetail />)} />
            <Route path="/admin/withdraw" element={guard("withdraw.view", <AdminWithdraw />)} />
            <Route path="/admin/tickets" element={guard("support.view", <AdminTickets />)} />
            <Route path="/admin/tickets/:id" element={guard("support.view", <AdminTicketDetail />)} />
            <Route path="/admin/contracts" element={guard("contracts.view", <AdminContracts />)} />
            <Route path="/admin/wami" element={guard("wami.view", <AdminWami />)} />
            <Route
              path="/admin/migrate"
              element={
                guard("migration.view", <AdminMigrate />)
              }
            />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return <BrowserRouter><AuthProvider><AppRoutes /><Toaster /></AuthProvider></BrowserRouter>;
}

export default App;
