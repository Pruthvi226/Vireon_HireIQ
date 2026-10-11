import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const user = await login(email, password);
      navigate(location.state?.from || (user.role === "ADMIN" ? "/admin" : user.role === "CANDIDATE" ? "/candidate" : "/recruiter"), { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return <main className="auth-page"><form className="panel auth-panel" onSubmit={submit}>
    <p className="eyebrow">Vireon HireIQ</p><h1>Sign in</h1>
    {error && <p role="alert" className="error-message">{error}</p>}
    <p className="muted">Sign in to your hiring workspace.</p>
    <label>Email<input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
    <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
    <button className="btn btn-primary" type="submit" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
    <Link to="/register">Create an account</Link>
  </form></main>;
}
