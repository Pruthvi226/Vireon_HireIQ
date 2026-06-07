import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import api from "../api";
import { useAuth } from "../auth";

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const [history, setHistory] = useState([]);
  const [progress, setProgress] = useState({ rollingAverageScore: 0, trend: [] });

  useEffect(() => {
    Promise.all([
      api.get("/api/user/interviews?page=0&size=10"),
      api.get("/api/user/progress"),
    ]).then(([h, p]) => {
      setHistory(h.data.content || []);
      setProgress(p.data);
    });
  }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold">Welcome, {user?.name}</h1>
        <div className="space-x-3">
          <Link className="btn-primary" to="/interview/start">Start Interview</Link>
          <button className="btn border border-slate-700" onClick={logout}>Logout</button>
        </div>
      </div>

      <motion.div initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="card">
        <p className="text-sm text-slate-300">Rolling score</p>
        <p className="text-4xl font-bold text-indigo-300">{progress.rollingAverageScore}</p>
      </motion.div>

      <div className="card">
        <h2 className="mb-4 text-xl font-semibold">Interview History</h2>
        <div className="space-y-2">
          {history.map((row) => (
            <Link key={row.id} to={`/interview/${row.id}/feedback`} className="block rounded-xl border border-slate-800 p-3 hover:border-indigo-400">
              <div className="flex justify-between">
                <span>{row.role} - {row.interviewType}</span>
                <span className="text-indigo-300">Score: {row.score ?? "N/A"}</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
