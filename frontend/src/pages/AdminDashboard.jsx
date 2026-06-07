import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth/AuthContext";

export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const [state, setState] = useState({
    users: [],
    candidates: [],
    jobs: [],
    analytics: null,
    platform: null,
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadAdminData() {
    setError("");
    setLoading(true);
    try {
      const [users, candidates, jobs, analytics, platform] = await Promise.all([
        api.adminUsers(),
        api.adminCandidates(),
        api.adminJobs(),
        api.adminAnalytics(),
        api.adminPlatformData(),
      ]);
      setState({ users, candidates, jobs, analytics, platform });
    } catch (err) {
      setError(err.message || "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAdminData();
  }, []);

  const metrics = [
    { label: "Users", value: state.analytics?.users ?? state.users.length },
    { label: "Candidates", value: state.analytics?.candidates ?? state.candidates.length },
    { label: "Jobs", value: state.analytics?.jobs ?? state.jobs.length },
    { label: "Matches", value: state.analytics?.matches ?? 0 },
  ];

  return (
    <main className="role-shell">
      <header className="role-topbar">
        <div>
          <span className="eyebrow">Admin dashboard</span>
          <h1>Platform control center</h1>
          <p>Signed in as {user?.name}</p>
        </div>
        <div className="role-actions">
          <Link className="btn btn-secondary" to="/recruiter">
            Recruiter console
          </Link>
          <button className="btn btn-outline" onClick={loadAdminData} disabled={loading}>
            Refresh
          </button>
          <button className="btn btn-primary" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      {error && <div className="alert alert-danger">{error}</div>}

      <section className="metrics-grid">
        {metrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <span className="metric-label">{metric.label}</span>
            <div className="metric-value-container">
              <strong className="metric-value">{metric.value}</strong>
            </div>
          </article>
        ))}
      </section>

      <section className="grid-2col">
        <article className="panel">
          <div className="panel-header">
            <h3>Users</h3>
            <span className="panel-subtitle">Registered role assignments</span>
          </div>
          <div className="data-table">
            {state.users.map((item) => (
              <div className="table-row" key={item.id}>
                <strong>{item.name}</strong>
                <span>{item.email}</span>
                <span className="badge badge-strong">{item.role}</span>
              </div>
            ))}
            {!state.users.length && <p className="empty-copy">No users found.</p>}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Jobs and analytics</h3>
            <span className="panel-subtitle">Recent hiring pipelines</span>
          </div>
          <div className="data-table">
            {state.analytics?.job_summaries?.map((job) => (
              <div className="table-row" key={job.job_id}>
                <strong>{job.title}</strong>
                <span>{job.candidates} candidates</span>
                <span>{job.average_score}% avg</span>
              </div>
            ))}
            {!state.analytics?.job_summaries?.length && <p className="empty-copy">No analytics generated yet.</p>}
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h3>Platform data</h3>
          <span className="panel-subtitle">Database and protected resource counts</span>
        </div>
        <div className="platform-grid">
          <span>Database</span>
          <code>{state.platform?.database || "Loading..."}</code>
          <span>Protected API groups</span>
          <code>/api/admin, /api/recruiter, /api/candidate</code>
        </div>
      </section>
    </main>
  );
}
