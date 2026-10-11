import { useEffect, useState } from "react";
import { api } from "../api";
import PageShell from "../components/PageShell";
import Pagination from "../components/Pagination";

export default function AdminDashboard() {
  const [users, setUsers] = useState({ items: [], total: 0 });
  const [data, setData] = useState(null);
  const [audit, setAudit] = useState([]);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    Promise.all([api.adminUsers({ page, search: query }), api.adminPlatformData(), api.systemAudit(20)]).then(([rows, overview, events]) => {
      if (active) { setUsers(rows); setData(overview); setAudit(events); }
    }).catch((err) => { if (active) setError(err.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [page, query]);

  return <PageShell title="Administration" description="Review workspace users, platform totals and recorded hiring actions.">
    {error && <p className="error-message" role="alert">{error}</p>}
    {loading && <p role="status">Loading workspace…</p>}
    {data && <section className="metrics-grid">{["users", "candidates", "jobs", "matches"].map((key) => <article className="panel" key={key}><p className="eyebrow">{key}</p><h2>{data[key] ?? 0}</h2></article>)}</section>}
    <section className="panel page-stack"><h2>Users</h2>
      <form className="page-actions" onSubmit={(event) => { event.preventDefault(); setPage(1); setQuery(search); }}>
        <label>Search users<input type="search" maxLength="120" placeholder="Name, email or role" value={search} onChange={(event) => setSearch(event.target.value)} /></label><button className="btn btn-primary" disabled={loading}>Search</button>
      </form>
      <div className="table-scroll"><table><caption className="sr-only">Workspace users</caption><thead><tr><th scope="col">Name</th><th scope="col">Email</th><th scope="col">Role</th><th scope="col">Company</th></tr></thead><tbody>{users.items.map((user) => <tr key={user.id}><td>{user.name}</td><td>{user.email}</td><td><span className="chip">{user.role}</span></td><td>{user.company_name || "—"}</td></tr>)}</tbody></table></div>
      {!loading && !users.total && <p>No users match your search.</p>}
      <Pagination page={page} total={users.total} onChange={setPage} disabled={loading} />
    </section>
    <section className="panel page-stack"><h2>Recent audit events</h2><p className="muted">Latest 20 events. Staff account provisioning is available through the local administrator command documented in the deployment guide.</p>
      {!audit.length && <p>No recorded actions yet.</p>}
      <ul className="audit-list">{audit.map((event) => <li key={event.event_id}><strong>{event.action}</strong><span>{event.actor_role || "System"} · {event.resource_type} {event.resource_id}</span><time>{new Date(event.created_at).toLocaleString()}</time></li>)}</ul>
    </section>
  </PageShell>;
}
