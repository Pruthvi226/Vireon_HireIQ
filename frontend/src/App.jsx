import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { useAuth } from "./auth/AuthContext";
import { motion, AnimatePresence } from "framer-motion";

const sampleResume = `Pruthvi Raj Panduga
pruthvi@example.com
Python, FastAPI, NLP, RAG, FAISS, Gemini API, Pandas, Scikit-learn, SQL
Projects: Built semantic resume screening APIs with embeddings, recruiter explanations and dashboards.
Experience: AI/ML backend projects with data preprocessing, model evaluation and documentation.
Education: IIIT Naya Raipur, Computer Science and AI coursework.`;

const sampleJob = `Artificial Intelligence Intern
QuickHyre AI builds ATS and HRMS automation for recruiters. Design and train AI/ML models, preprocess resume and job data, build NLP matching APIs, evaluate model accuracy, document experiments and create hiring dashboards. Skills: Python, FastAPI, Machine Learning, NLP, Scikit-learn, Pandas, FAISS, Gemini API, visualization, model evaluation. Internship duration 6 months with recruiter reports.`;

function App() {
  const { user, logout } = useAuth();
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [rankings, setRankings] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [interview, setInterview] = useState(null);
  const [gap, setGap] = useState(null);
  const [chatHistory, setChatHistory] = useState([
    {
      sender: "bot",
      text: "Hello! I am your HireIQ Assistant. Ask me questions like: 'Who knows Python and NLP?' or 'Show me candidates with FastAPI experience.'",
      evidence: null,
    },
  ]);
  const [resumeText, setResumeText] = useState(sampleResume);
  const [jobText, setJobText] = useState(sampleJob);
  const [candidateName, setCandidateName] = useState("");
  const [jobTitle, setJobTitle] = useState("Artificial Intelligence Intern");
  const [company, setCompany] = useState("QuickHyre AI");
  const [selectedJob, setSelectedJob] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState("");
  const [question, setQuestion] = useState("Who knows Python and NLP but lacks Computer Vision?");
  const [loading, setLoading] = useState(false);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  
  // Custom States
  const [activeTab, setActiveTab] = useState("overview");
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "dark");
  const [selectedCandidateDetail, setSelectedCandidateDetail] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [modelMetrics, setModelMetrics] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [systemOverview, setSystemOverview] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    refresh();
    fetchModelMetrics();
    fetchPlatformOps();
  }, [user?.role]);

  useEffect(() => {
    if (!selectedJob && jobs[0]) setSelectedJob(String(jobs[0].id));
    if (!selectedCandidate && candidates[0]) setSelectedCandidate(String(candidates[0].id));
  }, [jobs, candidates, selectedJob, selectedCandidate]);

  const top = rankings[0];
  const selectedJobId = useMemo(() => Number(selectedJob || jobs[0]?.id || 0), [selectedJob, jobs]);
  const selectedCandidateId = useMemo(() => Number(selectedCandidate || candidates[0]?.id || 0), [selectedCandidate, candidates]);

  const activeJobDetails = useMemo(() => {
    return jobs.find((j) => j.id === selectedJobId) || null;
  }, [jobs, selectedJobId]);

  const platformData = systemOverview?.data || {};
  const trafficStats = systemOverview?.traffic || {};
  const cacheInfo = systemOverview?.cache || {};
  const cacheStats = cacheInfo.stats || {};
  const cacheRequests = (cacheStats.hits || 0) + (cacheStats.misses || 0);
  const cacheHitRate = cacheRequests ? Math.round(((cacheStats.hits || 0) / cacheRequests) * 100) : 0;

  async function run(label, action) {
    setLoading(true);
    setError("");
    setSuccessMsg("");
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

  async function fetchModelMetrics() {
    try {
      const metrics = await api.experiment();
      setModelMetrics(metrics);
    } catch (err) {
      setModelMetrics(null);
    }
  }

  async function fetchPlatformOps() {
    try {
      const [health, overview] = await Promise.all([api.health(), api.systemOverview()]);
      setSystemHealth(health);
      setSystemOverview(overview);
      if (user?.role === "ADMIN") {
        setAuditEvents(await api.systemAudit(8));
      } else {
        setAuditEvents([]);
      }
    } catch (err) {
      setSystemHealth({ status: "offline", system: "Vireon HireIQ", database: "Unavailable" });
      setSystemOverview(null);
      setAuditEvents([]);
    }
  }

  async function seed() {
    await run("seed", async () => {
      const result = await api.seed();
      await refresh();
      setSelectedJob(String(result.job_id));
      setRankings(result.ranked || []);
      setAnalytics(await api.analytics(result.job_id));
      await fetchPlatformOps();
      setSuccessMsg("Demo data successfully seeded to database.");
    });
  }

  async function addCandidate() {
    await run("candidate", async () => {
      await api.createCandidate({ name: candidateName || null, resume_text: resumeText });
      setCandidateName("");
      setResumeText("");
      await refresh();
      await fetchPlatformOps();
      setSuccessMsg("Candidate profile parsed and stored.");
    });
  }

  async function addJob() {
    await run("job", async () => {
      const job = await api.createJob({ title: jobTitle || null, company: company || null, description: jobText });
      await refresh();
      setSelectedJob(String(job.id));
      setJobTitle("");
      setCompany("");
      setJobText("");
      await fetchPlatformOps();
      setSuccessMsg("Job description analyzed and tools extracted.");
    });
  }

  async function rank() {
    if (!selectedJobId) return;
    await run("rank", async () => {
      const rows = await api.rank(selectedJobId);
      setRankings(rows);
      setAnalytics(await api.analytics(selectedJobId));
      await fetchPlatformOps();
      setSuccessMsg("Candidate matching pipeline executed successfully.");
    });
  }

  async function inspectCandidate(candidateId) {
    if (!selectedJobId) {
      setError("Please select a job description first.");
      return;
    }
    const candidate = candidates.find((c) => c.id === candidateId);
    if (!candidate) return;

    setSelectedCandidateDetail(candidate);
    setDrawerLoading(true);
    try {
      const [gapData, interviewData] = await Promise.all([
        api.skillGap(candidateId, selectedJobId),
        api.interview(candidateId, selectedJobId),
      ]);
      setGap(gapData);
      setInterview(interviewData);
    } catch (err) {
      setError("Failed to fetch candidate insights: " + err.message);
    } finally {
      setDrawerLoading(false);
    }
  }

  async function handleFileUpload(file) {
    if (!file) return;
    await run("upload", async () => {
      const formData = new FormData();
      formData.append("file", file);
      const cleanName = file.name
        .replace(/\.[^/.]+$/, "")
        .replace(/[_-]/g, " ");
      formData.append("candidate_name", cleanName);

      await api.uploadResume(formData);
      await refresh();
      await fetchPlatformOps();
      setSuccessMsg(`File "${file.name}" uploaded and parsed successfully.`);
    });
  }

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  async function ask() {
    if (!question.trim()) return;
    const currentQuestion = question;
    setQuestion("");
    setChatHistory((prev) => [...prev, { sender: "user", text: currentQuestion }]);
    
    await run("chat", async () => {
      const response = await api.chat(currentQuestion, selectedJobId || null);
      setChatHistory((prev) => [
        ...prev,
        { sender: "bot", text: response.answer, evidence: response.evidence },
      ]);
      await fetchPlatformOps();
    });
  }

  async function downloadReport() {
    if (!selectedJobId) return;
    await run("report", async () => {
      const csv = await api.reportCsv(selectedJobId);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `vireon-job-${selectedJobId}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      await fetchPlatformOps();
      setSuccessMsg("CSV report exported.");
    });
  }

  return (
    <main className="app-shell">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div>
          <div className="brand">
            <span className="mark">VH</span>
            <div className="brand-text">
              <h1>Vireon HireIQ</h1>
              <p>AI Recruiter Console</p>
            </div>
          </div>
          
          <nav className="nav-links">
            <div
              className={`nav-item ${activeTab === "overview" ? "active" : ""}`}
              onClick={() => setActiveTab("overview")}
              id="nav-overview"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="9" />
                <rect x="14" y="3" width="7" height="5" />
                <rect x="14" y="12" width="7" height="9" />
                <rect x="3" y="16" width="7" height="5" />
              </svg>
              Overview
            </div>

            <div
              className={`nav-item ${activeTab === "job-lab" ? "active" : ""}`}
              onClick={() => setActiveTab("job-lab")}
              id="nav-job-lab"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
              </svg>
              Job Lab
            </div>

            <div
              className={`nav-item ${activeTab === "candidates" ? "active" : ""}`}
              onClick={() => setActiveTab("candidates")}
              id="nav-candidates"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
              Candidates
            </div>

            <div
              className={`nav-item ${activeTab === "rankings" ? "active" : ""}`}
              onClick={() => setActiveTab("rankings")}
              id="nav-rankings"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="6" y1="20" x2="6" y2="14" />
              </svg>
              Matching Matrix
            </div>

            <div
              className={`nav-item ${activeTab === "chat" ? "active" : ""}`}
              onClick={() => setActiveTab("chat")}
              id="nav-chat"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              HR Assistant
            </div>

            <div
              className={`nav-item ${activeTab === "model-labs" ? "active" : ""}`}
              onClick={() => setActiveTab("model-labs")}
              id="nav-model-labs"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
              Platform Ops
            </div>
          </nav>
        </div>

        <div className="sidebar-footer">
          {user && (
            <div className="user-chip">
              <span className="user-avatar">{user.name?.slice(0, 1) || "U"}</span>
              <div>
                <strong>{user.name}</strong>
                <p>{user.role}</p>
              </div>
            </div>
          )}
          <button className="btn btn-secondary w-full" onClick={seed} disabled={loading} id="btn-seed-demo">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{marginRight: "6px"}}>
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
            </svg>
            Seed Demo
          </button>
          
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "11px", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: 650 }}>Theme</span>
            <button
              className="theme-toggle-btn"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              title="Toggle Light/Dark Theme"
              id="btn-theme-toggle"
            >
              {theme === "dark" ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="5" />
                  <line x1="12" y1="1" x2="12" y2="3" />
                  <line x1="12" y1="21" x2="12" y2="23" />
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                  <line x1="1" y1="12" x2="3" y2="12" />
                  <line x1="21" y1="12" x2="23" y2="12" />
                  <line x1="4.22" y1="19.07" x2="5.64" y2="17.66" />
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </button>
          </div>
          <button className="btn btn-outline w-full" onClick={logout} id="btn-logout">
            Logout
          </button>
        </div>
      </aside>

      {/* Main Workspace Area */}
      <section className="workspace">
        {/* Topbar */}
        <header className="topbar">
          <div className="topbar-title">
            <p className="eyebrow">Recruiter Operations Console</p>
            <h2>
              {activeTab === "overview" && "Dashboard Overview"}
              {activeTab === "job-lab" && "Job Laboratory"}
              {activeTab === "candidates" && "Resume Ingestion Hub"}
              {activeTab === "rankings" && "Matching & Rankings"}
              {activeTab === "chat" && "AI Recruiter Assistant"}
              {activeTab === "model-labs" && "Platform Operations"}
            </h2>
          </div>
          
          <div className="selectors">
            <div className="form-group" style={{ width: "auto" }}>
              <select
                className="dropdown-select"
                value={selectedJob}
                onChange={(e) => setSelectedJob(e.target.value)}
                id="select-job-context"
              >
                <option value="">Select Job Description Context</option>
                {jobs.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.company ? `${job.company} - ` : ""}{job.title}
                  </option>
                ))}
              </select>
            </div>
            
            {activeTab === "rankings" && (
              <button
                className="btn btn-primary"
                onClick={rank}
                disabled={loading || !selectedJobId}
                id="btn-run-matching"
              >
                Match & Rank
              </button>
            )}

            {selectedJobId > 0 && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={downloadReport}
                id="link-csv-report"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
                </svg>
                CSV Export
              </button>
            )}
          </div>
        </header>

        {/* Global Loading and Error Banner */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="alert alert-danger"
              id="alert-error-banner"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </motion.div>
          )}

          {successMsg && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="alert alert-success"
              id="alert-success-banner"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              <span>{successMsg}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Tab Contents */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            transition={{ duration: 0.2 }}
            style={{ width: "100%", display: "flex", flexDirection: "column", gap: "24px" }}
          >
            {/* OVERVIEW TAB */}
            {activeTab === "overview" && (
              <>
                {/* Metric Cards Grid */}
                <div className="metrics-grid">
                  <div className="metric-card" id="card-metric-candidates">
                    <span className="metric-label">Parsed Resumes</span>
                    <div className="metric-value-container">
                      <strong className="metric-value">{candidates.length}</strong>
                      <span className="metric-icon-bg">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                          <circle cx="9" cy="7" r="4" />
                        </svg>
                      </span>
                    </div>
                  </div>

                  <div className="metric-card" id="card-metric-jobs">
                    <span className="metric-label">Active JDs</span>
                    <div className="metric-value-container">
                      <strong className="metric-value">{jobs.length}</strong>
                      <span className="metric-icon-bg">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
                        </svg>
                      </span>
                    </div>
                  </div>

                  <div className="metric-card" id="card-metric-avgscore">
                    <span className="metric-label">Avg Compatibility</span>
                    <div className="metric-value-container">
                      <strong className="metric-value">{analytics?.average_score ?? "--"}%</strong>
                      <span className="metric-icon-bg">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="10" />
                          <path d="M12 6v6l4 2" />
                        </svg>
                      </span>
                    </div>
                  </div>

                  <div className="metric-card" id="card-metric-shortlist">
                    <span className="metric-label">Shortlist Rate</span>
                    <div className="metric-value-container">
                      <strong className="metric-value">{analytics ? `${analytics.shortlist_ratio}%` : "--"}</strong>
                      <span className="metric-icon-bg">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      </span>
                    </div>
                  </div>
                </div>

                {/* Sub layout for analytics charts & overview */}
                <div className="grid-2col">
                  {/* Left Column - Active JD overview */}
                  <div className="panel" id="panel-role-overview">
                    <div className="panel-header">
                      <h3>Active Context Profile</h3>
                      <span className="panel-subtitle">Current Job Focus</span>
                    </div>
                    {activeJobDetails ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                        <div>
                          <h4 style={{ color: "var(--text-main)", fontSize: "18px", fontWeight: "700" }}>
                            {activeJobDetails.title}
                          </h4>
                          <p style={{ color: "var(--primary)", fontSize: "14px", fontWeight: "600", marginTop: "2px" }}>
                            {activeJobDetails.company || "Internal Placement"}
                          </p>
                        </div>
                        
                        <div className="grid-2col" style={{ gap: "12px", borderBottom: "1px solid var(--border-color)", paddingBottom: "16px" }}>
                          <div>
                            <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>Domain</span>
                            <p style={{ fontSize: "14px", fontWeight: "600" }}>{activeJobDetails.domain}</p>
                          </div>
                          <div>
                            <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>Level</span>
                            <p style={{ fontSize: "14px", fontWeight: "600" }}>{activeJobDetails.level}</p>
                          </div>
                        </div>

                        <div>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", display: "block", marginBottom: "8px" }}>
                            Primary Tools Extracted
                          </span>
                          <div className="chips-container">
                            {activeJobDetails.tools?.map((tool) => (
                              <span className="chip chip-success" key={tool}>{tool}</span>
                            ))}
                            {activeJobDetails.tools?.length === 0 && <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>None identified</span>}
                          </div>
                        </div>
                        
                        <div>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", display: "block", marginBottom: "8px" }}>
                            Job Description Quality Index
                          </span>
                          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                            <div className="score-progress-bar" style={{ height: "8px", flexGrow: 1 }}>
                              <div className="score-progress-fill" style={{ width: `${activeJobDetails.jd_quality_score}%` }}></div>
                            </div>
                            <span style={{ fontSize: "14px", fontWeight: "750" }}>{activeJobDetails.jd_quality_score}%</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="empty-state">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                          <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                          <polyline points="14 2 14 8 20 8" />
                        </svg>
                        <h4>No context job selected</h4>
                        <p>Create or select a job description to activate dashboard metrics.</p>
                      </div>
                    )}
                  </div>

                  {/* Right Column - Status breakdown & missing skills */}
                  <div className="panel" id="panel-overview-analytics">
                    <div className="panel-header">
                      <h3>Pipeline Breakdown</h3>
                      <span className="panel-subtitle">{candidates.length} Registered candidates</span>
                    </div>

                    {analytics ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                        <div>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>
                            Shortlist Categories
                          </span>
                          <div className="analytics-chart-container">
                            {["Reject", "Maybe", "Strong Match"].map((label) => {
                              const value = analytics.status_distribution[label] || 0;
                              const maxVal = Math.max(...Object.values(analytics.status_distribution), 1);
                              const heightPercentage = `${Math.max(10, (value / maxVal) * 160)}px`;
                              return (
                                <div key={label} className="chart-bar-col">
                                  <div className="chart-bar-pillar" style={{ height: heightPercentage }}></div>
                                  <span className="chart-bar-label">
                                    {label} ({value})
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        <div>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", display: "block", marginBottom: "8px" }}>
                            Critical Talent Skill Gaps
                          </span>
                          <div className="chips-container">
                            {analytics.common_missing_skills?.map((item) => (
                              <span className="chip chip-danger" key={item.skill}>
                                {item.skill} ({item.count})
                              </span>
                            ))}
                            {analytics.common_missing_skills?.length === 0 && (
                              <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>No skill gaps found</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="empty-state" style={{ height: "100%", justifyContent: "center" }}>
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                          <line x1="18" y1="20" x2="18" y2="10" />
                          <line x1="12" y1="20" x2="12" y2="4" />
                          <line x1="6" y1="20" x2="6" y2="14" />
                        </svg>
                        <h4>Analytical model offline</h4>
                        <p>Execute "Match & Rank" inside the Matching Matrix view to review pipeline graphs.</p>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}

            {/* JOB LAB TAB */}
            {activeTab === "job-lab" && (
              <div className="grid-2col">
                {/* Job Creation intake */}
                <div className="panel" id="panel-job-intake">
                  <div className="panel-header">
                    <h3>Analyze Job Description</h3>
                    <span className="panel-subtitle">Register a new profile context</span>
                  </div>

                  <div className="form-group">
                    <label htmlFor="input-job-title">Role Title</label>
                    <input
                      type="text"
                      className="text-input"
                      placeholder="e.g. Lead Machine Learning Engineer"
                      value={jobTitle}
                      onChange={(e) => setJobTitle(e.target.value)}
                      id="input-job-title"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="input-company">Company</label>
                    <input
                      type="text"
                      className="text-input"
                      placeholder="e.g. Vireon Technologies"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      id="input-company"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="input-jd-description">Job Description</label>
                    <textarea
                      className="textarea-input"
                      placeholder="Paste the job requirement text details here... (Min 30 chars)"
                      value={jobText}
                      onChange={(e) => setJobText(e.target.value)}
                      id="input-jd-description"
                    />
                  </div>

                  <button
                    className="btn btn-primary"
                    onClick={addJob}
                    disabled={loading || !jobText.trim()}
                    id="btn-save-job"
                  >
                    Analyze & Create Job
                  </button>
                </div>

                {/* Extracted JD Info Viewer */}
                <div className="panel" id="panel-job-details">
                  <div className="panel-header">
                    <h3>Extracted Requirements</h3>
                    <span className="panel-subtitle">Parsed results from active JD</span>
                  </div>

                  {activeJobDetails ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                      <div>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>Responsibilities</span>
                        <ul style={{ paddingLeft: "16px", marginTop: "8px", display: "flex", flexDirection: "column", gap: "6px" }}>
                          {activeJobDetails.responsibilities?.map((item, i) => (
                            <li key={i} style={{ fontSize: "13px", lineHeight: "1.4" }}>{item}</li>
                          ))}
                          {activeJobDetails.responsibilities?.length === 0 && <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>None parsed</span>}
                        </ul>
                      </div>

                      <div>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", display: "block", marginBottom: "8px" }}>
                          Required Skills & AI Weightage
                        </span>
                        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                          {Object.entries(activeJobDetails.skill_weightage || {}).map(([skill, weight]) => (
                            <div key={skill} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                              <span style={{ fontSize: "13px", fontWeight: "500" }}>{skill}</span>
                              <div style={{ display: "flex", alignItems: "center", gap: "8px", width: "160px" }}>
                                <div className="score-progress-bar" style={{ height: "4px", flexGrow: 1 }}>
                                  <div className="score-progress-fill" style={{ width: `${weight}%` }}></div>
                                </div>
                                <span style={{ fontSize: "12px", fontWeight: "700", minWidth: "30px", textAlign: "right" }}>{weight}%</span>
                              </div>
                            </div>
                          ))}
                          {Object.keys(activeJobDetails.skill_weightage || {}).length === 0 && (
                            <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>No weightage calculated</span>
                          )}
                        </div>
                      </div>

                      <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "16px" }}>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>Full JD Description Context</span>
                        <div
                          style={{
                            fontSize: "12px",
                            color: "var(--text-muted)",
                            marginTop: "8px",
                            maxHeight: "150px",
                            overflowY: "auto",
                            background: "rgba(0, 0, 0, 0.1)",
                            padding: "12px",
                            borderRadius: "8px",
                            lineHeight: "1.5",
                          }}
                        >
                          {activeJobDetails.description}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="empty-state">
                      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                      </svg>
                      <h4>No requirements available</h4>
                      <p>Analyze a new JD or select an existing one above to inspect NLP attributes.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* CANDIDATES TAB */}
            {activeTab === "candidates" && (
              <div className="grid-2col">
                {/* Resume parsing intake */}
                <div className="panel" id="panel-candidate-intake">
                  <div className="panel-header">
                    <h3>Ingest Candidate Profile</h3>
                    <span className="panel-subtitle">Text parsing & Document uploads</span>
                  </div>

                  {/* Drag and drop upload */}
                  <div
                    className={`file-upload-area ${dragActive ? "dragging" : ""}`}
                    onDragEnter={handleDrag}
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                    id="dropzone-resume"
                  >
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                    </svg>
                    <div>
                      <p style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-main)" }}>
                        Drag & Drop PDF/DOCX/TXT Resume Here
                      </p>
                      <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                        or click to select file from explorer
                      </p>
                    </div>
                    <input
                      type="file"
                      className="file-upload-input"
                      accept=".pdf,.docx,.txt"
                      onChange={async (e) => {
                        if (e.target.files && e.target.files[0]) {
                          await handleFileUpload(e.target.files[0]);
                        }
                      }}
                      id="input-resume-file"
                    />
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <span style={{ fontSize: "12px", color: "var(--text-muted)", textTransform: "uppercase", padding: "0 8px", background: "var(--bg-card)", zIndex: 2 }}>
                      OR PASTE RAW TEXT
                    </span>
                    <div style={{ position: "absolute", left: 32, right: 32, height: "1px", background: "var(--border-color)" }}></div>
                  </div>

                  <div className="form-group" style={{ marginTop: "8px" }}>
                    <label htmlFor="input-candidate-name">Candidate Name (Optional)</label>
                    <input
                      type="text"
                      className="text-input"
                      placeholder="e.g. Pruthvi Raj"
                      value={candidateName}
                      onChange={(e) => setCandidateName(e.target.value)}
                      id="input-candidate-name"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="input-candidate-resume">Raw Resume Text</label>
                    <textarea
                      className="textarea-input"
                      placeholder="Paste resume skills, experience, and certifications..."
                      value={resumeText}
                      onChange={(e) => setResumeText(e.target.value)}
                      id="input-candidate-resume"
                    />
                  </div>

                  <button
                    className="btn btn-primary"
                    onClick={addCandidate}
                    disabled={loading || !resumeText.trim()}
                    id="btn-save-candidate"
                  >
                    Parse & Save Profile
                  </button>
                </div>

                {/* Candidate database directory */}
                <div className="panel" id="panel-candidate-directory">
                  <div className="panel-header">
                    <h3>Candidate Database</h3>
                    <span className="panel-subtitle">{candidates.length} Profiles parsed</span>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "12px",
                      maxHeight: "680px",
                      overflowY: "auto",
                      paddingRight: "4px",
                    }}
                  >
                    {candidates.map((c) => (
                      <div
                        key={c.id}
                        className="candidate-row"
                        style={{ gridTemplateColumns: "1fr auto" }}
                        onClick={() => inspectCandidate(c.id)}
                      >
                        <div>
                          <span className="candidate-name">{c.name}</span>
                          <p className="candidate-meta">
                            {c.email ? `${c.email} • ` : ""}{c.phone ? `${c.phone}` : ""}
                          </p>
                          <div className="chips-container" style={{ marginTop: "10px" }}>
                            {c.skills?.slice(0, 5).map((skill) => (
                              <span className="chip" key={skill}>{skill}</span>
                            ))}
                            {c.skills?.length > 5 && <span className="chip">+{c.skills.length - 5} more</span>}
                          </div>
                        </div>
                        <div style={{ display: "flex", alignItems: "center" }}>
                          <button
                            className="btn btn-outline"
                            style={{ height: "32px", padding: "0 10px", borderRadius: "6px" }}
                          >
                            Details
                          </button>
                        </div>
                      </div>
                    ))}

                    {candidates.length === 0 && (
                      <div className="empty-state">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                          <circle cx="12" cy="12" r="10" />
                          <line x1="12" y1="8" x2="12" y2="16" />
                          <line x1="8" y1="12" x2="16" y2="12" />
                        </svg>
                        <h4>Database empty</h4>
                        <p>Upload a PDF resume or seed the demo dataset to populate the recruiter registry.</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* RANKINGS TAB */}
            {activeTab === "rankings" && (
              <div className="panel" id="panel-matching-matrix">
                <div className="panel-header">
                  <div>
                    <h3>Compatibility & Match Results</h3>
                    <span className="panel-subtitle">Sorted by HireIQ Final Composite Score</span>
                  </div>
                  {top && (
                    <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--primary)" }}>
                      Top Pick: {top.candidate_name} ({top.final_score}%)
                    </span>
                  )}
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {rankings.map((row) => (
                    <article
                      key={row.id || `${row.candidate_id}-${row.job_id}`}
                      className="candidate-row"
                      onClick={() => inspectCandidate(row.candidate_id)}
                    >
                      <div>
                        <strong className="candidate-name">{row.candidate_name}</strong>
                        <p className="candidate-explanation">{row.explanation}</p>
                        <div className="chips-container" style={{ marginTop: "10px" }}>
                          {row.matched_skills?.slice(0, 4).map((skill) => (
                            <span className="chip chip-success" key={skill}>{skill}</span>
                          ))}
                          {row.missing_skills?.slice(0, 4).map((skill) => (
                            <span className="chip chip-danger" key={skill}>{skill}</span>
                          ))}
                        </div>
                      </div>

                      <div>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>
                          Fit Status
                        </span>
                        <div style={{ marginTop: "4px" }}>
                          <span
                            className={`badge ${
                              row.status === "Strong Match"
                                ? "badge-strong"
                                : row.status === "Maybe"
                                ? "badge-maybe"
                                : "badge-reject"
                            }`}
                          >
                            {row.status}
                          </span>
                        </div>
                      </div>

                      <div>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>
                          Shortlist Prob
                        </span>
                        <p style={{ fontSize: "16px", fontWeight: "800", color: "var(--text-main)", marginTop: "4px" }}>
                          {row.shortlist_probability}%
                        </p>
                      </div>

                      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>
                          Match Score
                        </span>
                        <div className="radial-progress" style={{ marginTop: "4px" }}>
                          <svg>
                            <circle className="circle-bg" cx="45" cy="45" r="36" />
                            <circle
                              className="circle-val"
                              cx="45"
                              cy="45"
                              r="36"
                              style={{
                                strokeDashoffset: 251.2 - (251.2 * row.final_score) / 100,
                              }}
                            />
                          </svg>
                          <span className="radial-progress-value">{row.final_score}%</span>
                        </div>
                      </div>
                    </article>
                  ))}

                  {rankings.length === 0 && (
                    <div className="empty-state">
                      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
                        <line x1="4" y1="22" x2="4" y2="15" />
                      </svg>
                      <h4>No matching calculations found</h4>
                      <p>Select a context job description and click "Match & Rank" above to trigger vector matching.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* HR ASSISTANT CHAT TAB */}
            {activeTab === "chat" && (
              <div className="grid-2col" style={{ gridTemplateColumns: "1.4fr 1fr" }}>
                {/* Chat window */}
                <div className="panel" id="panel-chat-workspace" style={{ gap: "16px" }}>
                  <div className="panel-header">
                    <h3>Chat Workspace</h3>
                    <span className="panel-subtitle">Ask questions based on candidate evidence</span>
                  </div>

                  <div className="chat-container">
                    {chatHistory.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`chat-bubble ${
                          msg.sender === "user" ? "chat-bubble-user" : "chat-bubble-bot"
                        }`}
                      >
                        <p style={{ whiteSpace: "pre-wrap" }}>{msg.text}</p>
                        {msg.evidence && (
                          <div style={{ marginTop: "12px", borderTop: "1px solid var(--border-color)", paddingTop: "8px" }}>
                            <span style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", display: "block" }}>
                              Grounded Database Citations
                            </span>
                            <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "6px" }}>
                              {msg.evidence.map((item, i) => (
                                <div
                                  key={i}
                                  style={{
                                    fontSize: "12px",
                                    background: "rgba(255, 255, 255, 0.02)",
                                    border: "1px solid var(--border-color)",
                                    padding: "6px 8px",
                                    borderRadius: "4px",
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                  }}
                                >
                                  <strong>{item.candidate_name}</strong>
                                  <span style={{ fontSize: "11px", color: "var(--primary)", fontWeight: 700 }}>
                                    Match: {item.retrieval_score}%
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  <div className="chat-input-row">
                    <input
                      type="text"
                      className="text-input"
                      placeholder="Ask HR questions (e.g., Who knows Python and NLP but lacks Computer Vision?)"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !loading) ask();
                      }}
                      id="input-chat-question"
                    />
                    <button className="btn btn-primary" onClick={ask} disabled={loading || !question.trim()} id="btn-chat-send">
                      Ask AI
                    </button>
                  </div>
                </div>

                {/* Info and suggestion card */}
                <div className="panel" id="panel-chat-suggestions">
                  <div className="panel-header">
                    <h3>Query Suggestions</h3>
                    <span className="panel-subtitle">Suggested queries for grounded retrieval</span>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    {[
                      "Who knows Python and NLP but lacks Computer Vision?",
                      "Are there candidates with FastAPI skills?",
                      "Find candidates with Spring Boot or Docker experience.",
                      "Which candidate is the strongest fit for an AI Internship?",
                    ].map((suggestion, idx) => (
                      <div
                        key={idx}
                        className="interview-card"
                        style={{ cursor: "pointer", padding: "14px 18px" }}
                        onClick={() => setQuestion(suggestion)}
                      >
                        <span style={{ fontSize: "13px", fontWeight: "500", color: "var(--text-main)" }}>
                          "{suggestion}"
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* PLATFORM OPS TAB */}
            {activeTab === "model-labs" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                <div className="metrics-grid">
                  <div className="metric-card" id="card-api-p95">
                    <span className="metric-label">API p95</span>
                    <div className="metric-value-container">
                      <strong className="metric-value">{trafficStats.p95_latency_ms ?? 0}</strong>
                      <span className="metric-label">ms</span>
                    </div>
                  </div>

                  <div className="metric-card" id="card-cache-hit-rate">
                    <span className="metric-label">Cache Hit Rate</span>
                    <div className="metric-value-container">
                      <strong className="metric-value">{cacheHitRate}</strong>
                      <span className="metric-label">%</span>
                    </div>
                  </div>

                  <div className="metric-card" id="card-audit-events">
                    <span className="metric-label">Audit Events</span>
                    <div className="metric-value-container">
                      <strong className="metric-value">{platformData.audit_events ?? 0}</strong>
                    </div>
                  </div>

                  <div className="metric-card" id="card-system-uptime">
                    <span className="metric-label">Uptime</span>
                    <div className="metric-value-container">
                      <strong className="metric-value">{Math.floor((systemOverview?.service?.uptime_seconds || 0) / 60)}</strong>
                      <span className="metric-label">min</span>
                    </div>
                  </div>
                </div>

                <div className="grid-2col">
                  <div className="panel" id="panel-platform-readiness">
                    <div className="panel-header">
                      <h3>Platform Readiness</h3>
                      <span className="panel-subtitle">{systemOverview?.service?.environment || "local"}</span>
                    </div>

                    <div className="ops-row">
                      <span
                        className={`status-dot ${systemHealth?.status === "ok" ? "status-dot-ok" : "status-dot-bad"}`}
                      ></span>
                      <strong>{systemHealth?.status === "ok" ? `${systemHealth.system} Online` : "Backend Offline"}</strong>
                    </div>

                    <div className="platform-grid">
                      <span>Version</span>
                      <code>{systemOverview?.service?.version || systemHealth?.version || "Unknown"}</code>
                      <span>Request ID</span>
                      <code>{systemHealth?.request_id || "Pending request context"}</code>
                      <span>Database</span>
                      <code>{platformData.database_path || systemHealth?.database || "Unavailable"}</code>
                    </div>

                    <div className="system-check-list">
                      {(systemOverview?.readiness?.checks || []).map((check) => (
                        <div className="system-check" key={check.name}>
                          <span>{check.name}</span>
                          <span className={`badge ${check.status === "ok" ? "badge-strong" : "badge-reject"}`}>{check.status}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="panel" id="panel-model-metrics">
                    <div className="panel-header">
                      <h3>Scoring Pipeline</h3>
                      <span className="panel-subtitle">Hybrid matching baseline</span>
                    </div>

                    {modelMetrics ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                        <div>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>Model Name</span>
                          <p style={{ fontSize: "16px", fontWeight: "700", color: "var(--primary)", marginTop: "4px" }}>
                            {modelMetrics.model_name}
                          </p>
                        </div>

                        <div className="grid-2col" style={{ gap: "16px" }}>
                          {[
                            ["F1-Score", modelMetrics.f1_score],
                            ["Accuracy", modelMetrics.accuracy],
                            ["Precision", modelMetrics.precision],
                            ["Recall", modelMetrics.recall],
                          ].map(([label, value]) => (
                            <div className="ops-stat" key={label}>
                              <span>{label}</span>
                              <strong>{value}</strong>
                            </div>
                          ))}
                        </div>

                        <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "16px" }}>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", display: "block", marginBottom: "8px" }}>
                            Active scoring features
                          </span>
                          <div className="chips-container">
                            {modelMetrics.features?.map((f) => (
                              <span className="chip" key={f}>{f.replace("_", " ")}</span>
                            ))}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="empty-state">
                        <h4>Model metrics unavailable</h4>
                        <p>Backend benchmark endpoint is not responding.</p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="grid-2col">
                  <div className="panel" id="panel-service-topology">
                    <div className="panel-header">
                      <h3>Service Topology</h3>
                      <span className="panel-subtitle">Runtime boundaries</span>
                    </div>

                    <div className="topology-list">
                      {(systemOverview?.topology || []).map((node) => (
                        <div className="topology-item" key={node.name}>
                          <div>
                            <strong>{node.name}</strong>
                            <span>{node.type}</span>
                          </div>
                          <p>{node.responsibility}</p>
                          <code>{node.scale_unit}</code>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="panel" id="panel-cache-traffic">
                    <div className="panel-header">
                      <h3>Cache & Traffic</h3>
                      <span className="panel-subtitle">Live process counters</span>
                    </div>

                    <div className="platform-grid">
                      <span>Requests</span>
                      <code>{trafficStats.requests ?? 0}</code>
                      <span>Server errors</span>
                      <code>{trafficStats.server_errors ?? 0}</code>
                      <span>Cache entries</span>
                      <code>{cacheInfo.entries ?? 0}</code>
                      <span>Cache TTL</span>
                      <code>{cacheInfo.ttl_seconds ?? 0}s</code>
                    </div>

                    <div className="data-table">
                      {(trafficStats.top_paths || []).map((item) => (
                        <div className="table-row compact-row" key={item.route}>
                          <strong>{item.route}</strong>
                          <span>{item.count} hits</span>
                        </div>
                      ))}
                      {!(trafficStats.top_paths || []).length && <p className="empty-copy">No traffic sampled yet.</p>}
                    </div>
                  </div>
                </div>

                <div className="grid-2col">
                  <div className="panel" id="panel-audit-trail">
                    <div className="panel-header">
                      <h3>Audit Trail</h3>
                      <span className="panel-subtitle">Decision events</span>
                    </div>

                    <div className="data-table">
                      {auditEvents.map((event) => (
                        <div className="table-row" key={event.event_id}>
                          <strong>{event.action}</strong>
                          <span>{event.resource_type}{event.resource_id ? ` #${event.resource_id}` : ""}</span>
                          <span className="badge badge-strong">{event.actor_role || "SYSTEM"}</span>
                        </div>
                      ))}
                      {user?.role !== "ADMIN" && <p className="empty-copy">Admin role can view recent audit events.</p>}
                      {user?.role === "ADMIN" && !auditEvents.length && <p className="empty-copy">No audit events recorded yet.</p>}
                    </div>
                  </div>

                  <div className="panel" id="panel-scale-path">
                    <div className="panel-header">
                      <h3>Scale Path</h3>
                      <span className="panel-subtitle">Production evolution</span>
                    </div>

                    <div className="ops-list">
                      {(systemOverview?.scale_path || []).map((item, index) => (
                        <div className="ops-list-item" key={item}>
                          <span>{index + 1}</span>
                          <p>{item}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </section>

      {/* DETAIL MODAL DRAWER */}
      <AnimatePresence>
        {selectedCandidateDetail && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="drawer-backdrop"
            onClick={() => setSelectedCandidateDetail(null)}
            id="drawer-backdrop"
          >
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 220 }}
              className="drawer-content"
              onClick={(e) => e.stopPropagation()}
              id="drawer-panel"
            >
              {/* Close Button */}
              <button
                className="drawer-close"
                onClick={() => setSelectedCandidateDetail(null)}
                id="btn-close-drawer"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>

              {/* Drawer Header */}
              <div>
                <span className="chip chip-success" style={{ marginBottom: "8px" }}>
                  {interview?.fit_status || "Pending Analysis"}
                </span>
                <h3 style={{ fontSize: "28px", fontWeight: "800" }}>
                  {selectedCandidateDetail.name}
                </h3>
                <p style={{ color: "var(--text-muted)", fontSize: "14px", marginTop: "4px" }}>
                  {selectedCandidateDetail.email} • {selectedCandidateDetail.phone || "No phone link"}
                </p>
                {selectedCandidateDetail.links && selectedCandidateDetail.links.length > 0 && (
                  <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
                    {selectedCandidateDetail.links.map((link, i) => (
                      <a
                        key={i}
                        href={link.startsWith("http") ? link : `https://${link}`}
                        target="_blank"
                        rel="noreferrer"
                        className="chip chip-interactive"
                        style={{ fontSize: "11px" }}
                      >
                        {link.replace(/https?:\/\/(www\.)?/, "").slice(0, 24)}
                        {link.length > 24 ? "..." : ""}
                      </a>
                    ))}
                  </div>
                )}
              </div>

              {drawerLoading ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "300px", gap: "16px" }}>
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ animation: "spin 1.5s linear infinite" }}>
                    <path d="M22 12A10 10 0 1 1 12 2v2a8 8 0 1 0 8 8h2z" />
                  </svg>
                  <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>Calculating skill gap roadmaps and generating questions...</p>
                </div>
              ) : (
                <>
                  {/* Skill alignment section */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>Skill Overlap Alignment</span>
                    
                    {gap && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                        <div>
                          <p style={{ fontSize: "12px", color: "var(--success)", fontWeight: "700", marginBottom: "6px" }}>Matched Skills</p>
                          <div className="chips-container">
                            {gap.strong_skills?.map((skill) => (
                              <span className="chip chip-success" key={skill}>{skill}</span>
                            ))}
                            {gap.strong_skills?.length === 0 && <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>None identified</span>}
                          </div>
                        </div>

                        {gap.partial_skills && gap.partial_skills.length > 0 && (
                          <div>
                            <p style={{ fontSize: "12px", color: "var(--warning)", fontWeight: "700", marginBottom: "6px" }}>Partial Overlap</p>
                            <div className="chips-container">
                              {gap.partial_skills?.map((skill) => (
                                <span className="chip chip-warning" key={skill}>{skill}</span>
                              ))}
                            </div>
                          </div>
                        )}

                        <div>
                          <p style={{ fontSize: "12px", color: "var(--danger)", fontWeight: "700", marginBottom: "6px" }}>Missing Gaps</p>
                          <div className="chips-container">
                            {gap.missing_skills?.map((skill) => (
                              <span className="chip chip-danger" key={skill}>{skill}</span>
                            ))}
                            {gap.missing_skills?.length === 0 && <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>No missing gaps</span>}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Skill Gap Learning Roadmap */}
                  {gap?.roadmap && gap.roadmap.length > 0 && (
                    <div>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>Personalized Training Roadmap</span>
                      <div className="timeline">
                        {gap.roadmap.map((step) => (
                          <div className="timeline-item" key={step.week}>
                            <div className="timeline-dot"></div>
                            <div className="timeline-content">
                              <p className="timeline-week">Week {step.week}</p>
                              <strong className="timeline-title">Focus: {step.skill}</strong>
                              <p className="timeline-desc">{step.action}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Custom generated Interview Kit */}
                  {interview?.questions && interview.questions.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>Custom Recruiter Interview Kit</span>
                      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                        {interview.questions.map((q, i) => (
                          <div className="interview-card" key={i}>
                            <div className="interview-card-header">
                              <span className="interview-card-type">{q.type}</span>
                            </div>
                            <p className="interview-card-question">{q.question}</p>
                            {q.expected_signal && (
                              <p className="interview-card-signal">
                                <strong>Expected Signal:</strong> {q.expected_signal}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Spinning Loader CSS */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </main>
  );
}

export default App;
