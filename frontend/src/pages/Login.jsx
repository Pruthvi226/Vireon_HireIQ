import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { roleHome } from "../auth/apiAuth";

const demos = [
  { label: "Admin", email: "admin@vireon.ai", password: "admin123" },
  { label: "Recruiter", email: "recruiter@vireon.ai", password: "recruiter123" },
  { label: "Candidate", email: "candidate@vireon.ai", password: "candidate123" },
];

export default function Login() {
  const navigate = useNavigate();
  const { login, user } = useAuth();
  const [email, setEmail] = useState("recruiter@vireon.ai");
  const [password, setPassword] = useState("recruiter123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) navigate(roleHome(user.role), { replace: true });
  }, [user, navigate]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const loggedInUser = await login(email, password);
      navigate(roleHome(loggedInUser.role), { replace: true });
    } catch (err) {
      setError(err.message || "Invalid login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand">
          <span className="mark">VH</span>
          <div>
            <span className="eyebrow">Secure access</span>
            <h1>Vireon HireIQ</h1>
          </div>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <div>
            <h2>Sign in to your workspace</h2>
            <p>Role-aware dashboards for admins, recruiters, and candidates.</p>
          </div>

          {error && <div className="alert alert-danger">{error}</div>}

          <div className="form-group">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              className="text-input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              className="text-input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          <button className="btn btn-primary w-full" type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Login"}
          </button>
        </form>

        <div className="demo-strip">
          {demos.map((demo) => (
            <button
              key={demo.email}
              type="button"
              className="demo-pill"
              onClick={() => {
                setEmail(demo.email);
                setPassword(demo.password);
                setError("");
              }}
            >
              {demo.label}
            </button>
          ))}
        </div>

        <p className="auth-switch">
          New to Vireon? <Link to="/register">Create an account</Link>
        </p>
      </section>
    </main>
  );
}
