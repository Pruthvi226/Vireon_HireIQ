import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import SockJS from "sockjs-client";
import { Client } from "@stomp/stompjs";
import api from "../api";

export default function LiveInterviewPage() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [questionId, setQuestionId] = useState(location.state?.questionId ?? null);
  const [questionText, setQuestionText] = useState(location.state?.questionText ?? "Click 'Generate Question' to continue");
  const [answerText, setAnswerText] = useState("");
  const [feedback, setFeedback] = useState("");

  const wsUrl = useMemo(() => import.meta.env.VITE_WS_URL || "http://localhost:8080/ws/interview", []);

  useEffect(() => {
    const client = new Client({
      webSocketFactory: () => new SockJS(wsUrl),
      reconnectDelay: 3000,
    });

    client.onConnect = () => {
      client.subscribe(`/topic/interview.${id}`, (message) => {
        const evt = JSON.parse(message.body);
        if (evt.type === "QUESTION") {
          setQuestionId(evt.payload.questionId);
          setQuestionText(evt.payload.questionText);
        }
        if (evt.type === "ANSWER_ANALYZED") {
          setFeedback(evt.payload.feedbackText || "");
        }
      });
    };

    client.activate();
    return () => client.deactivate();
  }, [id, wsUrl]);

  const generateQuestion = async () => {
    const { data } = await api.post(`/api/interview/${id}/question`);
    setQuestionId(data.questionId);
    setQuestionText(data.questionText);
  };

  const submitAnswer = async () => {
    const { data } = await api.post(`/api/interview/${id}/answer`, { questionId, answerText });
    setFeedback(data.feedbackText || "");
    setAnswerText("");
    if (data.nextQuestion) {
      setQuestionId(data.nextQuestion.questionId);
      setQuestionText(data.nextQuestion.questionText);
    }
  };

  const finish = async () => {
    await api.post(`/api/interview/${id}/finish`);
    navigate(`/interview/${id}/feedback`);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <div className="card space-y-4">
        <h1 className="text-2xl font-semibold">Live Interview #{id}</h1>
        <p className="rounded-xl border border-slate-800 bg-slate-950 p-4">{questionText}</p>
        <button className="btn border border-slate-700" onClick={generateQuestion}>Generate Question</button>
        <textarea className="input min-h-32" placeholder="Type your answer..." value={answerText} onChange={(e) => setAnswerText(e.target.value)} />
        <div className="flex gap-3">
          <button className="btn-primary" onClick={submitAnswer}>Submit Answer</button>
          <button className="btn border border-slate-700" onClick={finish}>Finish Interview</button>
        </div>
      </div>
      <div className="card">
        <h2 className="mb-2 text-lg font-semibold">Real-time Feedback</h2>
        <p className="text-slate-300 whitespace-pre-wrap">{feedback || "Feedback will appear here after answer analysis."}</p>
      </div>
    </div>
  );
}
