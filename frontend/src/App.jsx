import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import StartInterviewPage from "./pages/StartInterviewPage";
import LiveInterviewPage from "./pages/LiveInterviewPage";
import FeedbackPage from "./pages/FeedbackPage";

function ProtectedRoute({ children }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/interview/start" element={<ProtectedRoute><StartInterviewPage /></ProtectedRoute>} />
        <Route path="/interview/:id/live" element={<ProtectedRoute><LiveInterviewPage /></ProtectedRoute>} />
        <Route path="/interview/:id/feedback" element={<ProtectedRoute><FeedbackPage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </div>
  );
}
