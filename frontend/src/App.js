import React, { lazy, Suspense } from "react";
import { BrowserRouter, MemoryRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/api/AuthContext";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import LabelLayout from "@/components/shared/LabelLayout";
import AdminLayout from "@/components/shared/AdminLayout";
import { RoutePrefetch, rolePage } from "@/routePrefetch";

const Landing = lazy(() => import("@/pages/Landing"));
const Login = lazy(() => import("@/pages/auth/Login"));
const Register = lazy(() => import("@/pages/auth/Register"));
const ForgotPassword = lazy(() => import("@/pages/auth/ForgotPassword"));
const ResetPassword = lazy(() => import("@/pages/auth/ResetPassword"));

const LabelDashboard = rolePage("label", () => import("@/pages/label/Dashboard"));
const LabelReleases = rolePage("label", () => import("@/pages/label/Releases"));
const UploadRelease = rolePage("label", () => import("@/pages/label/UploadRelease"));
const ReleaseDetail = rolePage("label", () => import("@/pages/label/ReleaseDetail"));
const LabelArtists = rolePage("label", () => import("@/pages/label/Artists"));
const LabelProfile = rolePage("label", () => import("@/pages/label/Profile"));
const LabelInvoices = rolePage("label", () => import("@/pages/label/Invoices"));
const LabelRoyalty = rolePage("label", () => import("@/pages/label/Royalty"));
const LabelWithdraw = rolePage("label", () => import("@/pages/label/Withdraw"));
const LabelSupportTickets = rolePage("label", () => import("@/pages/label/SupportTickets"));
const LabelSupportTicketDetail = rolePage("label", () => import("@/pages/label/SupportTicketDetail"));
const LabelContract = rolePage("label", () => import("@/pages/label/Contract"));
const LabelWami = rolePage("label", () => import("@/pages/label/Wami"));

const AdminDashboard = rolePage("admin", () => import("@/pages/admin/Dashboard"));
const AdminAnalytics = rolePage("admin", () => import("@/pages/admin/Analytics"));
const AnalyticsAudit = rolePage("admin", () => import("@/pages/admin/AnalyticsAudit"));
const AdminLabels = rolePage("admin", () => import("@/pages/admin/Labels"));
const AdminLabelDetail = rolePage("admin", () => import("@/pages/admin/LabelDetail"));
const RoyaltyAdjustments = rolePage("admin", () => import("@/pages/admin/RoyaltyAdjustments"));
import { AppPreferencesProvider } from "@/contexts/AppPreferencesContext";
import { AudioPreviewProvider } from "@/contexts/AudioPreviewContext";
const RoleWebsitePreview = lazy(() => import("@/components/admin/access/RoleWebsitePreview").then((module) => ({ default: module.RoleWebsitePreview })));
const AdminReleases = rolePage("admin", () => import("@/pages/admin/Releases"));
const AdminReleaseDetail = rolePage("admin", () => import("@/pages/admin/ReleaseDetail"));
const AdminArtists = rolePage("admin", () => import("@/pages/admin/Artists"));
const AdminPayments = rolePage("admin", () => import("@/pages/admin/Payments"));
const AdminAddonOrders = rolePage("admin", () => import("@/pages/admin/AddonOrders"));
const AdminCMS = rolePage("admin", () => import("@/pages/admin/CMS"));
const AdminUsers = rolePage("admin", () => import("@/pages/admin/AdminUsers"));
const AdminActivityLogs = rolePage("admin", () => import("@/pages/admin/ActivityLogs"));
const AdminRoyaltyImport = rolePage("admin", () => import("@/pages/admin/RoyaltyImport"));
const AdminRoyaltyDetail = rolePage("admin", () => import("@/pages/admin/RoyaltyDetail"));
const AdminWithdraw = rolePage("admin", () => import("@/pages/admin/Withdraw"));
const AdminTickets = rolePage("admin", () => import("@/pages/admin/Tickets"));
const AdminTicketDetail = rolePage("admin", () => import("@/pages/admin/TicketDetail"));
const AdminContracts = rolePage("admin", () => import("@/pages/admin/Contracts"));
const AdminWami = rolePage("admin", () => import("@/pages/admin/Wami"));
const AdminMigrate = rolePage("admin", () => import("@/pages/admin/Migrate"));
const AdminKycReviews = rolePage("admin", () => import("@/pages/admin/KycReviews"));
const AdminAccessControl = rolePage("admin", () => import("@/pages/admin/AccessControl"));
const MultiLabelMerge = rolePage("admin", () => import("@/pages/admin/MultiLabelMerge"));
const MyCompensation = rolePage("admin", () => import("@/pages/admin/MyCompensation"));
const CompensationAdmin = rolePage("admin", () => import("@/pages/admin/CompensationAdmin"));
const MultiLabelRequest = lazy(() => import("@/pages/MultiLabelRequest"));
const RateChangeQueue = rolePage("admin", () => import("@/pages/admin/RateChangeQueue"));
const WorkQueue = rolePage("admin", () => import("@/pages/admin/WorkQueue"));
const BankVerifications = rolePage("admin", () => import("@/pages/admin/BankVerifications"));
const StaffManagement = rolePage("admin", () => import("@/pages/admin/StaffManagement"));
const Attendance = rolePage("admin", () => import("@/pages/admin/Attendance"));
const StaffConfiguration = rolePage("admin", () => import("@/pages/admin/StaffConfiguration"));
const WorkspaceStatus = rolePage("admin", () => import("@/pages/admin/WorkspaceStatus"));
const Performance = rolePage("admin", () => import("@/pages/admin/Performance"));
const MyPerformance = rolePage("admin", () => import("@/pages/admin/MyPerformance"));
const PerformanceConfig = rolePage("admin", () => import("@/pages/admin/PerformanceConfig"));
const XenditReconciliation = rolePage("admin", () => import("@/pages/admin/XenditReconciliation"));
const Refunds = rolePage("admin", () => import("@/pages/admin/Refunds"));
const AdminUiSettings = rolePage("admin", () => import("@/pages/admin/UiSettings"));
const AdminMaintenance = rolePage("admin", () => import("@/pages/admin/Maintenance"));
const AdminNotifications = rolePage("admin", () => import("@/pages/admin/Notifications"));
import { Toaster } from "@/components/ui/sonner";

const ArtistDashboard = rolePage("artist", () => import("@/pages/artist/Dashboard"));

const LABEL_ROLES = ["label"];
const ARTIST_ROLES = ["artist"];
const ADMIN_ROLES = ["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content", "admin_marketing", "admin_ui", "admin_custom", "admin_package_manager"];
const guard = (permission, element) => <ProtectedRoute permission={permission}>{element}</ProtectedRoute>;

function AppRoutes() {
  return (
    <Suspense fallback={<div role="status" className="p-8 text-center text-zinc-400">Memuat halaman…</div>}><Routes>
          {/* Public */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/ajukan-multi-label" element={<MultiLabelRequest />} />
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
            <Route path="/admin/analytics/audit" element={guard("analytics.manage", <AnalyticsAudit />)} />
            <Route path="/admin/labels" element={guard("labels.view", <AdminLabels />)} />
            <Route path="/admin/labels/rate-import" element={<Navigate to="/admin/labels" replace />} />
            <Route path="/admin/labels/:id" element={guard("labels.view", <AdminLabelDetail />)} />
            <Route path="/admin/rate-changes" element={guard("labels.rate.request.view", <RateChangeQueue />)} />
            <Route path="/admin/multi-label" element={guard("labels.multi_label.view", <MultiLabelMerge />)} />
            <Route path="/admin/compensation/me" element={guard("compensation.view_own", <MyCompensation />)} />
            <Route path="/admin/compensation/payroll" element={guard("compensation.payroll.view", <CompensationAdmin />)} />
            <Route path="/admin/compensation/staff" element={guard("compensation.view_team", <CompensationAdmin />)} />
            <Route path="/admin/compensation/bonus" element={guard("compensation.bonus.view", <CompensationAdmin />)} />
            <Route path="/admin/compensation/bonus-rules" element={guard("compensation.bonus.rules.manage", <CompensationAdmin />)} />
            <Route path="/admin/compensation/adjustments" element={guard("compensation.adjustment.create", <CompensationAdmin />)} />
            <Route path="/admin/work" element={guard("work.view", <WorkQueue />)} />
            <Route path="/admin/bank-verifications" element={<ProtectedRoute roles={["super_admin"]}><BankVerifications /></ProtectedRoute>} />
            <Route path="/admin/maintenance" element={<ProtectedRoute roles={["super_admin"]}><AdminMaintenance /></ProtectedRoute>} />
            <Route path="/admin/staff" element={guard("staff.view", <StaffManagement />)} />
            <Route path="/admin/staff/configuration" element={guard("staff.config.manage", <StaffConfiguration />)} />
            <Route path="/admin/attendance" element={guard("staff.attendance.view", <Attendance />)} />
            <Route path="/admin/performance" element={guard("performance.view_team", <Performance />)} />
            <Route path="/admin/performance/configuration" element={guard("performance.config.manage", <PerformanceConfig />)} />
            <Route path="/admin/my-performance" element={guard("performance.view_own", <MyPerformance />)} />
            <Route path="/admin/status" element={guard("dashboard.view", <WorkspaceStatus />)} />
            <Route path="/admin/kyc" element={guard("kyc.view", <AdminKycReviews />)} />
            <Route path="/admin/artists" element={guard("artists.view", <AdminArtists />)} />
            <Route path="/admin/releases" element={guard("releases.view", <AdminReleases />)} />
            <Route path="/admin/releases/:id" element={guard("releases.view", <AdminReleaseDetail />)} />
            <Route path="/admin/payments" element={guard("payments.view", <AdminPayments />)} />
            <Route path="/admin/addon-orders" element={guard("addon.view", <AdminAddonOrders />)} />
            <Route path="/admin/cms" element={guard("cms.view", <AdminCMS />)} />
            <Route path="/admin/admin-users" element={guard("access.users.view", <AdminUsers />)} />
            <Route path="/admin/access" element={guard("access.roles.view", <AdminAccessControl />)} />
            <Route path="/admin/ui-settings" element={guard("ui.settings.view", <AdminUiSettings />)} />
            <Route path="/admin/notifications" element={guard("notifications.view", <AdminNotifications />)} />
            <Route path="/admin/activity-logs" element={guard("activity.view", <AdminActivityLogs />)} />
            <Route path="/admin/royalty" element={guard("royalty.view", <AdminRoyaltyImport />)} />
            <Route path="/admin/royalty-adjustments" element={guard("royalty.manage", <RoyaltyAdjustments />)} />
            <Route path="/admin/royalty/:id" element={guard("royalty.view", <AdminRoyaltyDetail />)} />
            <Route path="/admin/withdraw" element={guard("withdraw.view", <AdminWithdraw />)} />
            <Route path="/admin/xendit-reconciliation" element={guard("payments.view", <XenditReconciliation />)} />
            <Route path="/admin/refunds" element={guard("payments.refund", <Refunds />)} />
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
    </Routes></Suspense>
  );
}

function App() {
  if (window.location.pathname === "/admin/role-preview") return <MemoryRouter><AppPreferencesProvider preview><Suspense fallback={<div role="status">Memuat halaman…</div>}><RoleWebsitePreview /></Suspense></AppPreferencesProvider></MemoryRouter>;
  return <BrowserRouter><AppPreferencesProvider><AuthProvider><RoutePrefetch /><AudioPreviewProvider><AppRoutes /><Toaster /></AudioPreviewProvider></AuthProvider></AppPreferencesProvider></BrowserRouter>;
}

export default App;
