import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import api from "../api.js";
import { useAuth } from "../AuthContext.jsx";
import BookCard from "../components/BookCard.jsx";

export default function ForYou() {
  const { user } = useAuth();
  const [results, setResults] = useState([]);
  const [alpha, setAlpha] = useState(0.5);
  const [isColdStart, setIsColdStart] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async (a) => {
    setLoading(true);
    try {
      const { data } = await api.get("/recommendations/for-you", { params: { alpha: a, top_n: 12 } });
      setResults(data.results);
      setIsColdStart(data.is_cold_start);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(alpha);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!user) return <Navigate to="/login" replace />;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-display font-semibold">For you</h1>
          {isColdStart && (
            <p className="text-sm text-ink/60 mt-1">
              You haven't rated any books yet, so these are popular picks -- rate a few books to get personalized recommendations.
            </p>
          )}
        </div>
        {!isColdStart && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-ink/60">collaborative</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={alpha}
              onChange={(e) => {
                const v = parseFloat(e.target.value);
                setAlpha(v);
                load(v);
              }}
            />
            <span className="text-ink/60">content</span>
          </div>
        )}
      </div>

      {loading ? (
        <p className="text-ink/50">Loading...</p>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3">
          {results.map((b) => (
            <BookCard key={b.book_id} book={b} />
          ))}
        </div>
      )}
    </div>
  );
}
