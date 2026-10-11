import { Navigate } from "react-router-dom";
import { roleHome, } from "./apiAuth";
import { useAuth } from "./AuthContext";

export default function ProtectedRoute({ allowedRoles, children }) {
  const { user, loading } = useAuth();
  if (loading) return <p role="status">Checking your session…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (!allowedRoles.includes(user.role)) return <Navigate to={roleHome(user.role)} replace />;
  return children;
}
