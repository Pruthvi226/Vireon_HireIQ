import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth/AuthContext";

const starterResume = `Demo Candidate
candidate@vireon.ai
Skills: Python, SQL, REST API, Git, Machine Learning
Projects: Built a resume scoring dashboard with model evaluation and API integrations.
Experience: Internship projects focused on data preprocessing and documentation.
Education: Computer Science graduate with AI coursework.`;

export default function CandidateDashboard() {
  const { user, logout } = useAuth();
  const [resumeText, setResumeText] = useState(starterResume);
  const [jobs, setJobs] = useState([]);
  const [profile, setProfile] = useState(null);
  const [selectedJob, setSelectedJob] = useState("");
  const [score, setScore] = useState(null);
  const [gap, setGap] = useState(null);
  const [suggestions, setSuggestions] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedJobId = useMemo(() => Number(selectedJob || jobs[0]?.id || 0), [selectedJob, jobs]);

  async function load() {
    setError("");
    try {
      const [jobRows, candidateProfile] = await Promise.all([api.jobs(), api.candidateProfile()]);
      setJobs(jobRows);
      setProfile(candidateProfile);
      if (!selectedJob && jobRows[0]) setSelectedJob(String(jobRows[0].id));
    } catch (err) {
      setError(err.message || "Failed to load candidate workspace");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function run(action, doneMessage) {
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      await action();
      if (doneMessage) setSuccess(doneMessage);
    } catch (err) {
      setError(err.message || "Request failed");
    } finally {
      setLoading(false);
    }
  }

  async function saveResume() {
    await run(async () => {
      await api.createCandidate({ name: user?.name || null, resume_text: resumeText });
      await load();
    }, "Resume uploaded and linked to your candidate account.");
  }

  async function analyze() {
    if (!selectedJobId) {
      setError("Select a job before requesting candidate insights.");
      return;
    }
    await run(async () => {
      const [scoreData, gapData, improvementData] = await Promise.all([
        api.candidateAtsScore(selectedJobId),
        api.candidateSkillGap(selectedJobId),
        api.candidateResumeImprovement(selectedJobId),
      ]);
      setScore(scoreData);
      setGap(gapData);
      setSuggestions(improvementData);
    }, "Candidate analysis refreshed.");
  }

  const latestResume = profile?.resumes?.[0];

  return (
    <main className="role-shell candidate-shell">
      <header className="role-topbar">
        <div>
          <span className="eyebrow">Candidate dashboard</span>
          <h1>Your ATS readiness workspace</h1>
          <p>{user?.email}</p>
        </div>
        <div className="role-actions">
          <button className="btn btn-secondary" onClick={load} disabled={loading}>
            Refresh
          </button>
          <button className="btn btn-primary" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <section className="grid-2col">
        <article className="panel">
          <div className="panel-header">
            <h3>Resume upload</h3>
            <span className="panel-subtitle">Private to your candidate account</span>
          </div>
          <div className="form-group">
            <label htmlFor="candidate-resume">Resume text</label>
            <textarea
              id="candidate-resume"
              className="textarea-input"
              value={resumeText}
              onChange={(event) => setResumeText(event.target.value)}
            />
          </div>
          <button className="btn btn-primary" onClick={saveResume} disabled={loading || resumeText.trim().length < 20}>
            Upload resume
          </button>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>ATS score</h3>
            <span className="panel-subtitle">Match against an active job</span>
          </div>
          <div className="form-group">
            <label htmlFor="candidate-job">Job</label>
            <select
              id="candidate-job"
              className="dropdown-select"
              value={selectedJob}
              onChange={(event) => setSelectedJob(event.target.value)}
            >
              <option value="">Select job</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.company ? `${job.company} - ` : ""}
                  {job.title}
                </option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary" onClick={analyze} disabled={loading || !selectedJobId || !latestResume}>
            Analyze my fit
          </button>

          {score && (
            <div className="score-card">
              <strong>{score.ats_score}%</strong>
              <span>{score.status}</span>
              <p>{score.match.explanation}</p>
            </div>
          )}
          {!latestResume && <p className="empty-copy">Upload your resume before requesting an ATS score.</p>}
        </article>
      </section>

      <section className="grid-2col">
        <article className="panel">
          <div className="panel-header">
            <h3>Skill gap analysis</h3>
            <span className="panel-subtitle">Strong skills and gaps</span>
          </div>
          <div className="chips-container">
            {gap?.strong_skills?.map((skill) => (
              <span className="chip chip-success" key={skill}>{skill}</span>
            ))}
            {gap?.missing_skills?.map((skill) => (
              <span className="chip chip-danger" key={skill}>{skill}</span>
            ))}
            {!gap && <p className="empty-copy">Run analysis to see skill fit.</p>}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Resume improvements</h3>
            <span className="panel-subtitle">Actionable suggestions</span>
          </div>
          <div className="data-table">
            {suggestions?.suggestions?.map((item) => (
              <div className="table-row" key={item}>
                <span>{item}</span>
              </div>
            ))}
            {!suggestions && <p className="empty-copy">Suggestions will appear after analysis.</p>}
          </div>
        </article>
      </section>
    </main>
  );
}
