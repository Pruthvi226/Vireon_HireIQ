import { useEffect, useMemo, useState } from "react";
import { api } from "./api";

const sampleResume = `Pruthvi Raj Panduga
pruthvi@example.com
Python, FastAPI, NLP, RAG, FAISS, Gemini API, Pandas, Scikit-learn, SQL
Projects: Built semantic resume screening APIs with embeddings, recruiter explanations and dashboards.
Experience: AI/ML backend projects with data preprocessing, model evaluation and documentation.
Education: IIIT Naya Raipur, Computer Science and AI coursework.`;

const sampleJob = `Artificial Intelligence Intern
QuickHyre AI builds ATS and HRMS automation for recruiters. Design and train AI/ML models, preprocess resume and job data, build NLP matching APIs, evaluate model accuracy, document experiments and create hiring dashboards. Skills: Python, FastAPI, Machine Learning, NLP, Scikit-learn, Pandas, FAISS, Gemini API, visualization, model evaluation. Internship duration 6 months with recruiter reports.`;

function App() {
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [rankings, setRankings] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [interview, setInterview] = useState(null);
  const [gap, setGap] = useState(null);
  const [chat, setChat] = useState(null);
  const [resumeText, setResumeText] = useState(sampleResume);
  const [jobText, setJobText] = useState(sampleJob);
  const [candidateName, setCandidateName] = useState("");
  const [jobTitle, setJobTitle] = useState("Artificial Intelligence Intern");
  const [company, setCompany] = useState("QuickHyre AI");
  const [selectedJob, setSelectedJob] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState("");
  const [question, setQuestion] = useState("Who knows Python and NLP but lacks Computer Vision?");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (!selectedJob && jobs[0]) setSelectedJob(String(jobs[0].id));
    if (!selectedCandidate && candidates[0]) setSelectedCandidate(String(candidates[0].id));
  }, [jobs, candidates, selectedJob, selectedCandidate]);

  const top = rankings[0];
  const selectedJobId = useMemo(() => Number(selectedJob || jobs[0]?.id || 0), [selectedJob, jobs]);
  const selectedCandidateId = useMemo(() => Number(selectedCandidate || candidates[0]?.id || 0), [selectedCandidate, candidates]);

  async function run(label, action) {
    setLoading(true);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function refresh() {
    const [candidateRows, jobRows] = await Promise.all([api.candidates(), api.jobs()]);
    setCandidates(candidateRows);
    setJobs(jobRows);
  }

  async function seed() {
    await run("seed", async () => {
      const result = await api.seed();
      await refresh();
      setSelectedJob(String(result.job_id));
      setRankings(result.ranked || []);
      setAnalytics(await api.analytics(result.job_id));
    });
  }

  async function addCandidate() {
    await run("candidate", async () => {
      await api.createCandidate({ name: candidateName || null, resume_text: resumeText });
      await refresh();
    });
  }

  async function addJob() {
    await run("job", async () => {
      const job = await api.createJob({ title: jobTitle || null, company: company || null, description: jobText });
      await refresh();
      setSelectedJob(String(job.id));
    });
  }

  async function rank() {
    if (!selectedJobId) return;
    await run("rank", async () => {
      const rows = await api.rank(selectedJobId);
      setRankings(rows);
      setAnalytics(await api.analytics(selectedJobId));
    });
  }

  async function generateInterview() {
    if (!selectedCandidateId || !selectedJobId) return;
    await run("interview", async () => {
      setInterview(await api.interview(selectedCandidateId, selectedJobId));
      setGap(await api.skillGap(selectedCandidateId, selectedJobId));
    });
  }

  async function ask() {
    await run("chat", async () => setChat(await api.chat(question, selectedJobId || null)));
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="mark">VH</span>
          <div>
            <h1>Vireon HireIQ</h1>
            <p>Hiring intelligence console</p>
          </div>
        </div>
        <button onClick={seed} disabled={loading}>Seed Demo</button>
        <button onClick={rank} disabled={loading || !selectedJobId}>Rank Candidates</button>
        <a href={`http://localhost:8000/api/reports/job/${selectedJobId || 1}?format=csv`}>CSV Report</a>
        {error && <p className="error">{error}</p>}
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">ATS AI backend</p>
            <h2>Recruiter Operations</h2>
          </div>
          <div className="selectors">
            <select value={selectedJob} onChange={(e) => setSelectedJob(e.target.value)}>
              <option value="">Job</option>
              {jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}
            </select>
            <select value={selectedCandidate} onChange={(e) => setSelectedCandidate(e.target.value)}>
              <option value="">Candidate</option>
              {candidates.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.name}</option>)}
            </select>
            <button onClick={generateInterview} disabled={loading || !selectedJobId || !selectedCandidateId}>Interview Kit</button>
          </div>
        </header>

        <section className="metrics-grid">
          <Metric label="Candidates" value={candidates.length} />
          <Metric label="Jobs" value={jobs.length} />
          <Metric label="Average Score" value={analytics?.average_score ?? "--"} />
          <Metric label="Shortlist Ratio" value={analytics ? `${analytics.shortlist_ratio}%` : "--"} />
        </section>

        <section className="main-grid">
          <div className="panel intake">
            <div className="panel-head">
              <h3>Resume Intake</h3>
              <button onClick={addCandidate} disabled={loading}>Save Candidate</button>
            </div>
            <input value={candidateName} onChange={(e) => setCandidateName(e.target.value)} placeholder="Candidate name" />
            <textarea value={resumeText} onChange={(e) => setResumeText(e.target.value)} />
          </div>

          <div className="panel intake">
            <div className="panel-head">
              <h3>Job Lab</h3>
              <button onClick={addJob} disabled={loading}>Create Job</button>
            </div>
            <div className="split">
              <input value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} placeholder="Role title" />
              <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Company" />
            </div>
            <textarea value={jobText} onChange={(e) => setJobText(e.target.value)} />
          </div>
        </section>

        <section className="main-grid">
          <div className="panel">
            <div className="panel-head">
              <h3>Ranking</h3>
              <span>{top ? `${top.candidate_name}: ${top.final_score}%` : "No ranking"}</span>
            </div>
            <div className="ranking-list">
              {rankings.map((row) => (
                <article key={row.id || `${row.candidate_id}-${row.job_id}`} className="rank-row">
                  <div>
                    <strong>{row.candidate_name}</strong>
                    <p>{row.status} - {row.explanation}</p>
                  </div>
                  <div className="score">
                    <span style={{ "--score": `${row.final_score}%` }} />
                    <b>{row.final_score}%</b>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <h3>Analytics</h3>
              <span>{analytics?.total_candidates ?? 0} profiles</span>
            </div>
            <div className="chart-row">
              {Object.entries(analytics?.status_distribution || {}).map(([label, value]) => (
                <div key={label} className="bar">
                  <span style={{ height: `${Math.max(12, value * 34)}px` }} />
                  <small>{label}</small>
                </div>
              ))}
            </div>
            <h4>Missing Skills</h4>
            <div className="chips">
              {(analytics?.common_missing_skills || []).map((item) => <span key={item.skill}>{item.skill} ({item.count})</span>)}
            </div>
          </div>
        </section>

        <section className="main-grid">
          <div className="panel">
            <div className="panel-head">
              <h3>Interview Kit</h3>
              <span>{interview?.fit_status || "Pending"}</span>
            </div>
            <div className="question-list">
              {(interview?.questions || []).map((item, index) => (
                <article key={`${item.type}-${index}`}>
                  <strong>{item.type}</strong>
                  <p>{item.question}</p>
                  {item.expected_signal && <small>{item.expected_signal}</small>}
                </article>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <h3>HR Assistant</h3>
              <button onClick={ask} disabled={loading}>Ask</button>
            </div>
            <textarea className="short" value={question} onChange={(e) => setQuestion(e.target.value)} />
            {chat && <p className="answer">{chat.answer}</p>}
            <div className="chips">
              {(gap?.missing_skills || []).map((skill) => <span key={skill}>{skill}</span>)}
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

export default App;
