import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { motion } from "framer-motion";
import api from "../api";
import { useAuth } from "../auth";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });

  const onSubmit = async (e) => {
    e.preventDefault();
    const { data } = await api.post("/api/auth/login", form);
    login(data);
    navigate("/dashboard");
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-md items-center px-4">
      <motion.form initial={{ opacity: 0 }} animate={{ opacity: 1 }} onSubmit={onSubmit} className="card w-full space-y-4">
        <h1 className="text-2xl font-semibold">Login</h1>
        <input className="input" placeholder="Email" type="email" onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <input className="input" placeholder="Password" type="password" onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <button className="btn-primary w-full" type="submit">Sign In</button>
        <p className="text-sm text-slate-300">New here? <Link className="text-indigo-300" to="/register">Create account</Link></p>
      </motion.form>
    </div>
  );
}
