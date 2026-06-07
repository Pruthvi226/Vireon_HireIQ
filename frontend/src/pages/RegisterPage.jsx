import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { motion } from "framer-motion";
import api from "../api";
import { useAuth } from "../auth";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "SDE", experienceLevel: "Fresher" });

  const onSubmit = async (e) => {
    e.preventDefault();
    const { data } = await api.post("/api/auth/register", form);
    login(data);
    navigate("/dashboard");
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-md items-center px-4">
      <motion.form initial={{ opacity: 0 }} animate={{ opacity: 1 }} onSubmit={onSubmit} className="card w-full space-y-4">
        <h1 className="text-2xl font-semibold">Register</h1>
        <input className="input" placeholder="Name" onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className="input" placeholder="Email" type="email" onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <input className="input" placeholder="Password" type="password" onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <input className="input" placeholder="Role (SDE/Analyst)" onChange={(e) => setForm({ ...form, role: e.target.value })} value={form.role} />
        <input className="input" placeholder="Experience" onChange={(e) => setForm({ ...form, experienceLevel: e.target.value })} value={form.experienceLevel} />
        <button className="btn-primary w-full" type="submit">Create Account</button>
        <p className="text-sm text-slate-300">Already registered? <Link className="text-indigo-300" to="/login">Sign in</Link></p>
      </motion.form>
    </div>
  );
}
