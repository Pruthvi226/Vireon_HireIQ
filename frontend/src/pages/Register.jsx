import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "CANDIDATE" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register(form);
      navigate("/candidate", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return <main className="auth-page"><form className="panel auth-panel" onSubmit={submit}>
    <p className="eyebrow">Vireon HireIQ</p><h1>Create account</h1>
    {error && <p role="alert" className="error-message">{error}</p>}
    <p className="muted">Create a candidate account to improve your resume and explore job fit.</p>
    <label>Name<input autoComplete="name" minLength="2" maxLength="120" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label>
    <label>Email<input type="email" autoComplete="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></label>
    <label>Password<input type="password" autoComplete="new-password" minLength="8" maxLength="72" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required /></label>
    <button className="btn btn-primary" type="submit" disabled={submitting}>{submitting ? "Creating account…" : "Register"}</button><Link to="/login">Back to sign in</Link>
  </form></main>;
}
