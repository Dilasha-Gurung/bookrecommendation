import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await register(username, email, password);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.error || "Could not create account.");
    }
  };

  return (
    <div className="max-w-sm mx-auto mt-10">
      <h1 className="text-2xl font-display font-semibold mb-6">Sign up</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm mb-1 text-ink/70">Username</label>
          <input
            className="w-full border border-rule rounded-lg px-3 py-2 bg-white/60 focus:outline-none focus:ring-2 focus:ring-gold"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-sm mb-1 text-ink/70">Email</label>
          <input
            type="email"
            className="w-full border border-rule rounded-lg px-3 py-2 bg-white/60 focus:outline-none focus:ring-2 focus:ring-gold"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-sm mb-1 text-ink/70">Password</label>
          <input
            type="password"
            className="w-full border border-rule rounded-lg px-3 py-2 bg-white/60 focus:outline-none focus:ring-2 focus:ring-gold"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
        </div>
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button className="w-full py-2 rounded-lg bg-forest text-paper font-medium hover:bg-forestlight transition-colors">
          Create account
        </button>
      </form>
      <p className="text-sm text-ink/60 mt-4">
        Already have an account? <Link to="/login" className="text-forest underline">Log in</Link>
      </p>
    </div>
  );
}
