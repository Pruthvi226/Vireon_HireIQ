import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";
import { roleHome } from "./auth/apiAuth";
import Login from "./pages/Login";
import Register from "./pages/Register";

const AdminDashboard = lazy(() => import("./pages/AdminDashboard"));
const CandidateDashboard = lazy(() => import("./pages/CandidateDashboard"));
const RecruiterDashboard = lazy(() => import("./pages/RecruiterDashboard"));

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <p role="status">Checking your session…</p>;
  return <Navigate to={user ? roleHome(user.role) : "/login"} replace />;
}

export default function RootApp() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<main className="auth-page" role="status">Loading workspace…</main>}>
        <Routes>
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={["ADMIN"]}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recruiter"
            element={
              <ProtectedRoute allowedRoles={["RECRUITER", "ADMIN"]}>
                <RecruiterDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/candidate"
            element={
              <ProtectedRoute allowedRoles={["CANDIDATE", "ADMIN"]}>
                <CandidateDashboard />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}
