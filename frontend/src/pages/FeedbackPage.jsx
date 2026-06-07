import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../api";

export default function FeedbackPage() {
  const { id } = useParams();
  const [fb, setFb] = useState(null);

  useEffect(() => {
    api.get(`/api/interview/${id}/feedback`).then((res) => setFb(res.data));
  }, [id]);

  if (!fb) return <div className="p-6">Loading feedback...</div>;

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-6">
      <div className="card">
        <h1 className="text-2xl font-semibold">Interview Feedback #{id}</h1>
        <p className="mt-2 text-4xl text-indigo-300">Overall: {fb.overallScore}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="card">Communication: {fb.communicationScore}</div>
        <div className="card">Technical: {fb.technicalScore}</div>
        <div className="card">Confidence: {fb.confidenceScore}</div>
      </div>
      <div className="card"><h2 className="font-semibold">Strengths</h2><p className="text-slate-300 whitespace-pre-wrap">{fb.strengths}</p></div>
      <div className="card"><h2 className="font-semibold">Weaknesses</h2><p className="text-slate-300 whitespace-pre-wrap">{fb.weaknesses}</p></div>
      <div className="card"><h2 className="font-semibold">Suggestions</h2><p className="text-slate-300 whitespace-pre-wrap">{fb.suggestions}</p></div>
    </div>
  );
}
