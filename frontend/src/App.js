import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/api/AuthContext";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import LabelLayout from "@/components/shared/LabelLayout";
import AdminLayout from "@/components/shared/AdminLayout";

import Landing from "@/pages/Landing";
import Login from "@/pages/auth/Login";
import Register from "@/pages/auth/Register";
import ForgotPassword from "@/pages/auth/ForgotPassword";
import ResetPassword from "@/pages/auth/ResetPassword";

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

import ArtistDashboard from "@/pages/artist/Dashboard";

const LABEL_ROLES = ["label"];
const ARTIST_ROLES = ["artist"];
const ADMIN_ROLES = ["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content"];

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
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
            <Route path="/admin/dashboard" element={<AdminDashboard />} />
            <Route
              path="/admin/analytics"
              element={
                <ProtectedRoute roles={["super_admin", "admin_finance"]}>
                  <AdminAnalytics />
                </ProtectedRoute>
              }
            />
            <Route path="/admin/labels" element={<AdminLabels />} />
            <Route path="/admin/labels/rate-import" element={<ProtectedRoute roles={["super_admin", "admin_finance"]}><LabelRateImport /></ProtectedRoute>} />
            <Route path="/admin/labels/:id" element={<AdminLabelDetail />} />
            <Route path="/admin/artists" element={<AdminArtists />} />
            <Route path="/admin/releases" element={<AdminReleases />} />
            <Route path="/admin/releases/:id" element={<AdminReleaseDetail />} />
            <Route path="/admin/payments" element={<AdminPayments />} />
            <Route path="/admin/cms" element={<AdminCMS />} />
            <Route path="/admin/admin-users" element={<AdminUsers />} />
            <Route path="/admin/activity-logs" element={<AdminActivityLogs />} />
            <Route path="/admin/royalty" element={<AdminRoyaltyImport />} />
            <Route path="/admin/royalty/:id" element={<AdminRoyaltyDetail />} />
            <Route path="/admin/withdraw" element={<AdminWithdraw />} />
            <Route path="/admin/tickets" element={<AdminTickets />} />
            <Route path="/admin/tickets/:id" element={<AdminTicketDetail />} />
            <Route path="/admin/contracts" element={<AdminContracts />} />
            <Route path="/admin/wami" element={<AdminWami />} />
            <Route
              path="/admin/migrate"
              element={
                <ProtectedRoute roles={["super_admin"]}>
                  <AdminMigrate />
                </ProtectedRoute>
              }
            />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
