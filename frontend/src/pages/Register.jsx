import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { roleHome } from "../auth/apiAuth";

export default function Register() {
  const navigate = useNavigate();
  const { register, user } = useAuth();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "RECRUITER",
    company_name: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) navigate(roleHome(user.role), { replace: true });
  }, [user, navigate]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const nextUser = await register({
        ...form,
        company_name: form.company_name.trim() || null,
      });
      navigate(roleHome(nextUser.role), { replace: true });
    } catch (err) {
      setError(err.message || "Registration failed");
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
            <span className="eyebrow">Create account</span>
            <h1>Join Vireon HireIQ</h1>
          </div>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {error && <div className="alert alert-danger">{error}</div>}

          <div className="form-group">
            <label htmlFor="register-name">Name</label>
            <input
              id="register-name"
              className="text-input"
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
              required
              minLength={2}
            />
          </div>

          <div className="form-group">
            <label htmlFor="register-email">Email</label>
            <input
              id="register-email"
              className="text-input"
              type="email"
              value={form.email}
              onChange={(event) => updateField("email", event.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="register-password">Password</label>
            <input
              id="register-password"
              className="text-input"
              type="password"
              value={form.password}
              onChange={(event) => updateField("password", event.target.value)}
              minLength={8}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="register-role">Role</label>
            <select
              id="register-role"
              className="dropdown-select"
              value={form.role}
              onChange={(event) => updateField("role", event.target.value)}
            >
              <option value="RECRUITER">Recruiter</option>
              <option value="CANDIDATE">Candidate</option>
              <option value="ADMIN">Admin</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="register-company">Company name</label>
            <input
              id="register-company"
              className="text-input"
              value={form.company_name}
              onChange={(event) => updateField("company_name", event.target.value)}
              placeholder={form.role === "CANDIDATE" ? "Optional" : "e.g. QuickHyre AI"}
            />
          </div>

          <button className="btn btn-primary w-full" type="submit" disabled={loading}>
            {loading ? "Creating account..." : "Register"}
          </button>
        </form>

        <p className="auth-switch">
          Already have access? <Link to="/login">Sign in</Link>
        </p>
      </section>
    </main>
  );
}
