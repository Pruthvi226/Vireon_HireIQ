import { Link, Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { roleHome } from "./apiAuth";

export default function ProtectedRoute({ allowedRoles, children }) {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <main className="auth-page">
        <section className="auth-card auth-card-compact">
          <span className="eyebrow">Session</span>
          <h1>Checking access</h1>
          <p>Restoring your secure workspace.</p>
        </section>
      </main>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    return (
      <main className="auth-page">
        <section className="auth-card auth-card-compact">
          <span className="eyebrow">Access denied</span>
          <h1>Your role cannot open this workspace.</h1>
          <p>
            Logged in as {user.role}. Return to your dashboard or sign in with another account.
          </p>
          <div className="auth-actions">
            <Link className="btn btn-primary" to={roleHome(user.role)}>
              Go to dashboard
            </Link>
            <button className="btn btn-secondary" onClick={logout}>
              Logout
            </button>
          </div>
        </section>
      </main>
    );
  }

  return children;
}
