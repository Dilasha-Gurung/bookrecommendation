import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="border-b border-rule bg-paper/95 backdrop-blur sticky top-0 z-10">
      <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <span className="w-1.5 h-6 spine rounded-sm" />
          <span className="font-display text-xl font-semibold tracking-tight">Shelf</span>
        </Link>

        <nav className="flex items-center gap-6 text-sm font-medium">
          <Link to="/" className="hover:text-forest transition-colors">Browse</Link>
          {user && (
            <Link to="/for-you" className="hover:text-forest transition-colors">For you</Link>
          )}
          {user ? (
            <div className="flex items-center gap-3">
              <span className="text-ink/60">{user.username}</span>
              <button
                onClick={() => { logout(); navigate("/"); }}
                className="px-3 py-1.5 rounded-full border border-rule hover:border-forest hover:text-forest transition-colors"
              >
                Log out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Link to="/login" className="hover:text-forest transition-colors">Log in</Link>
              <Link
                to="/register"
                className="px-3 py-1.5 rounded-full bg-forest text-paper hover:bg-forestlight transition-colors"
              >
                Sign up
              </Link>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
