// frontend/src/App.tsx
// Route table. Counterpart of the include_router calls in backend/src/main.py.
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { RequireAccess, RequireAuth } from "@/auth/guards";
import { canWriteEntries, homePathFor, isAdmin } from "@/auth/permissions";
import { AppShell } from "@/components/layout/AppShell";
import AdminPage from "@/pages/admin/AdminPage";
import ChangePinPage from "@/pages/ChangePinPage";
import GateHomePage from "@/pages/gate/GateHomePage";
import PersonInPage from "@/pages/gate/PersonInPage";
import TruckInPage from "@/pages/gate/TruckInPage";
import InsidePage from "@/pages/inside/InsidePage";
import LoginPage from "@/pages/LoginPage";
import LogPage from "@/pages/log/LogPage";
import NotFoundPage from "@/pages/NotFoundPage";

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
            <Route path="gate" element={<GateHomePage />} />
            <Route path="gate/truck" element={<TruckInPage />} />
            <Route path="gate/visitor" element={<PersonInPage kind="visitors" />} />
            <Route path="gate/staff" element={<PersonInPage kind="staff" />} />
          </Route>

          <Route path="inside" element={<InsidePage />} />
          <Route path="log" element={<LogPage />} />

          <Route element={<RequireAccess allow={isAdmin} />}>
            <Route path="admin" element={<AdminPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
