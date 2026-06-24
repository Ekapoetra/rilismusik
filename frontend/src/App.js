import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/api/AuthContext";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import LabelLayout from "@/components/shared/LabelLayout";
import AdminLayout from "@/components/shared/AdminLayout";
import ComingSoon from "@/components/shared/ComingSoon";

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

import AdminDashboard from "@/pages/admin/Dashboard";
import AdminLabels from "@/pages/admin/Labels";
import AdminLabelDetail from "@/pages/admin/LabelDetail";
import AdminReleases from "@/pages/admin/Releases";
import AdminReleaseDetail from "@/pages/admin/ReleaseDetail";
import AdminArtists from "@/pages/admin/Artists";
import AdminPayments from "@/pages/admin/Payments";
import AdminCMS from "@/pages/admin/CMS";
import AdminUsers from "@/pages/admin/AdminUsers";
import AdminActivityLogs from "@/pages/admin/ActivityLogs";

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
            <Route path="/label/royalty" element={<ComingSoon title="Royalti" description="Laporan royalti, filter per bulan/artist/lagu/platform/negara, dan download PDF/Excel akan tersedia setelah modul CSV import royalty selesai (Fase 2)." />} />
            <Route path="/label/withdraw" element={<ComingSoon title="Withdraw" description="Sistem withdraw dengan jendela tanggal 1–14 (request), 15–20 (payment) akan tersedia setelah ledger royalti aktif (Fase 2)." />} />
            <Route path="/label/support" element={<ComingSoon title="Support Ticket" description="Takedown, edit metadata, edit audio/cover, Content ID akan tersedia di Fase 3." />} />
          </Route>

          {/* Artist */}
          <Route element={<ProtectedRoute roles={ARTIST_ROLES}><ArtistDashboard /></ProtectedRoute>} path="/artist/dashboard" />

          {/* Admin */}
          <Route element={<ProtectedRoute roles={ADMIN_ROLES}><AdminLayout /></ProtectedRoute>}>
            <Route path="/admin/dashboard" element={<AdminDashboard />} />
            <Route path="/admin/labels" element={<AdminLabels />} />
            <Route path="/admin/labels/:id" element={<AdminLabelDetail />} />
            <Route path="/admin/artists" element={<AdminArtists />} />
            <Route path="/admin/releases" element={<AdminReleases />} />
            <Route path="/admin/releases/:id" element={<AdminReleaseDetail />} />
            <Route path="/admin/payments" element={<AdminPayments />} />
            <Route path="/admin/cms" element={<AdminCMS />} />
            <Route path="/admin/admin-users" element={<AdminUsers />} />
            <Route path="/admin/activity-logs" element={<AdminActivityLogs />} />
            <Route path="/admin/royalty" element={<ComingSoon title="Royalty Import" description="Upload CSV Believe (EUR), set kurs IDR per periode, preview matched/unmatched, publish laporan. (Fase 2)" />} />
            <Route path="/admin/withdraw" element={<ComingSoon title="Withdraw Management" description="Approve/Reject withdraw, generate invoice pembayaran. (Fase 2)" />} />
            <Route path="/admin/tickets" element={<ComingSoon title="Support Tickets" description="Kelola tiket dari label: takedown, edit metadata, edit audio, Content ID. (Fase 3)" />} />
            <Route path="/admin/contracts" element={<ComingSoon title="Contracts" description="Upload kontrak, set masa berlaku, perpanjang. (Fase 3)" />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
