import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

export default function StartInterviewPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ role: "SDE", interviewType: "TECHNICAL", interviewerMode: "STRICT" });

  const onStart = async () => {
    const { data } = await api.post("/api/interview/start", form);
    navigate(`/interview/${data.interviewId}/live`, { state: data });
  };

  return (
    <div className="mx-auto max-w-xl p-6">
      <div className="card space-y-4">
        <h1 className="text-2xl font-semibold">Start Interview</h1>
        <input className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
        <select className="input" value={form.interviewType} onChange={(e) => setForm({ ...form, interviewType: e.target.value })}>
          <option value="HR">HR</option>
          <option value="TECHNICAL">TECHNICAL</option>
          <option value="BEHAVIORAL">BEHAVIORAL</option>
        </select>
        <select className="input" value={form.interviewerMode} onChange={(e) => setForm({ ...form, interviewerMode: e.target.value })}>
          <option value="STRICT">STRICT</option>
          <option value="FRIENDLY">FRIENDLY</option>
          <option value="STRESS">STRESS</option>
        </select>
        <button className="btn-primary w-full" onClick={onStart}>Begin</button>
      </div>
    </div>
  );
}
