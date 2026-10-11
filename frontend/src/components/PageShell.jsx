import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function PageShell({ title, description, children }) {
  const { user, logout } = useAuth();
  return <main className="role-shell">
    <a className="skip-link" href="#page-content">Skip to content</a>
    <header className="role-topbar">
      <div><p className="eyebrow">Vireon HireIQ · {user?.role}</p><h1>{title}</h1><p className="muted">{description}</p></div>
      <div className="page-actions">{user?.role === "ADMIN" && <Link className="btn btn-outline" to="/recruiter">Recruiter workspace</Link>}<button className="btn btn-outline" onClick={logout}>Sign out</button></div>
    </header>
    <div id="page-content" className="page-stack">{children}</div>
  </main>;
}
