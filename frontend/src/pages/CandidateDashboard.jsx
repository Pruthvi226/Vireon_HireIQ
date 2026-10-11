import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth/AuthContext";
import PageShell from "../components/PageShell";
import Pagination from "../components/Pagination";
import ScoreBadge from "../components/ScoreBadge";

export default function CandidateDashboard() {
  const { user } = useAuth();
  const [resumes, setResumes] = useState([]);
  const [jobs, setJobs] = useState({ items: [], total: 0 });
  const [page, setPage] = useState(1);
  const [selectedJob, setSelectedJob] = useState("");
  const [selectedResume, setSelectedResume] = useState("");
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    setError("");
    Promise.all([api.candidateProfile(), api.jobs({ page, status: "open" })]).then(([profile, rows]) => {
      if (!active) return;
      setResumes(profile.resumes);
      setJobs(rows);
      setSelectedResume((current) => current || String(profile.resumes[0]?.id || ""));
      setSelectedJob(String(rows.items[0]?.id || ""));
      setResult(null);
    }).catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [page]);

  async function run(action) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  async function saveResume(event) {
    event.preventDefault();
    await run(async () => {
      const candidate = await api.createCandidate({ name: user.name, resume_text: text });
      setResumes((rows) => [candidate, ...rows]); setSelectedResume(String(candidate.id));
      setText(""); setResult(null); setNotice("Resume saved. Choose a job to review your fit.");
    });
  }

  async function upload(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    await run(async () => {
      const form = new FormData(); form.append("file", file); form.append("candidate_name", user.name);
      const candidate = await api.uploadResume(form);
      setResumes((rows) => [candidate, ...rows]); setSelectedResume(String(candidate.id));
      setResult(null); setNotice("Resume uploaded successfully.");
    });
  }

  async function analyze() {
    await run(async () => {
      const [score, gap, advice] = await Promise.all([
        api.candidateAtsScore(selectedJob, selectedResume),
        api.candidateSkillGap(selectedJob, selectedResume),
        api.candidateResumeImprovement(selectedJob, selectedResume),
      ]);
      setResult({ score, gap, advice });
    });
  }

  return <PageShell title={`Welcome, ${user?.name || "candidate"}`} description="Build a clear resume and understand how your evidence matches an open role.">
    {error && <p className="error-message" role="alert">{error}</p>}
    {notice && <p className="success-message" role="status">{notice}</p>}
    <div className="grid-2col">
      <section className="panel page-stack"><h2>Your resume</h2><p className="muted">Upload TXT, PDF or DOCX, up to 5 MB. PDFs need selectable text.</p>
        <label>Upload resume<input type="file" accept=".txt,.pdf,.docx" onChange={upload} disabled={busy} /></label>
        <form className="page-stack" onSubmit={saveResume}>
          <label>Or paste resume text<textarea rows="8" minLength="20" maxLength="100000" required value={text} onChange={(event) => setText(event.target.value)} /></label>
          <button className="btn btn-primary" disabled={busy || text.trim().length < 20}>{busy ? "Working…" : "Save resume"}</button>
        </form>
      </section>
      <section className="panel page-stack"><h2>Explore your job fit</h2>
        {!resumes.length && <p className="muted">Save your first resume to unlock a fit review.</p>}
        <label>Resume<select value={selectedResume} disabled={busy} onChange={(event) => { setSelectedResume(event.target.value); setResult(null); }}>
          <option value="">Choose a resume</option>{resumes.map((resume) => <option key={resume.id} value={resume.id}>{resume.name} · {new Date(resume.created_at).toLocaleDateString()}</option>)}
        </select></label>
        <label>Open job<select value={selectedJob} disabled={busy} onChange={(event) => { setSelectedJob(event.target.value); setResult(null); }}>
          <option value="">Choose a job</option>{jobs.items.map((job) => <option key={job.id} value={job.id}>{job.title}{job.company ? ` · ${job.company}` : ""}</option>)}
        </select></label>
        {!jobs.total && <p className="muted">No open jobs yet. Check back when recruiters publish a role.</p>}
        <Pagination page={page} total={jobs.total} onChange={setPage} disabled={busy} />
        <button className="btn btn-primary" disabled={busy || !selectedJob || !selectedResume} onClick={analyze}>{busy ? "Analyzing…" : "Review my fit"}</button>
      </section>
    </div>
    {result && <section className="panel page-stack" aria-live="polite">
      <h2>{result.score.job.title}</h2><div className="page-actions"><ScoreBadge score={result.score.ats_score} /><strong>{result.score.status}</strong></div>
      <p className="muted">This heuristic score describes resume evidence. It is not a hiring decision or a validated probability.</p>
      <p>{result.score.match.explanation}</p>
      <h3>Skills to strengthen</h3><div className="chips-container">{result.gap.missing_skills.map((skill) => <span className="chip" key={skill}>{skill}</span>)}{!result.gap.missing_skills.length && <p>No direct skill gaps found.</p>}</div>
      <h3>Resume improvements</h3><ul className="content-list">{result.advice.suggestions.map((suggestion) => <li key={suggestion}>{suggestion}</li>)}</ul>
      {result.gap.roadmap.length > 0 && <><h3>Learning roadmap</h3><ol className="content-list">{result.gap.roadmap.map((item) => <li key={item.week}>Week {item.week}: {item.skill} — {item.action}</li>)}</ol></>}
    </section>}
  </PageShell>;
}
