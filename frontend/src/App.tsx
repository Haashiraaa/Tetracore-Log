// frontend/src/App.tsx
// Route table. Counterpart of the include_router calls in backend/src/main.py.
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { RequireAccess, RequireAuth } from "@/auth/guards";
import { canWriteEntries, homePathFor, isAdmin, isSuperAdmin } from "@/auth/permissions";
import { AppShell } from "@/components/layout/AppShell";
import AdminPage from "@/pages/admin/AdminPage";
import ChangePinPage from "@/pages/ChangePinPage";
import GatePage from "@/pages/gate/GatePage";
import InsidePage from "@/pages/inside/InsidePage";
import LoginPage from "@/pages/LoginPage";
import LogPage from "@/pages/log/LogPage";
import NotFoundPage from "@/pages/NotFoundPage";
import SuperAdminPage from "@/pages/superadmin/SuperAdminPage";

function HomeRedirect() {
  const { profile } = useAuth();
  return <Navigate to={homePathFor(profile)} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        <Route path="/change-pin" element={<ChangePinPage />} />

        <Route element={<AppShell />}>
          <Route index element={<HomeRedirect />} />

          <Route element={<RequireAccess allow={canWriteEntries} />}>
            <Route path="gate" element={<GatePage />} />
          </Route>

          <Route path="inside" element={<InsidePage />} />
          <Route path="log" element={<LogPage />} />

          <Route element={<RequireAccess allow={isAdmin} />}>
            <Route path="admin" element={<AdminPage />} />
          </Route>
          <Route element={<RequireAccess allow={isSuperAdmin} />}>
            <Route path="super-admin" element={<SuperAdminPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
