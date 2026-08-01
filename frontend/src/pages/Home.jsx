import React, { useEffect, useState } from "react";
import api from "../api.js";
import { useAuth } from "../AuthContext.jsx";
import BookCard from "../components/BookCard.jsx";

export default function Home() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(false);

  const [pickerBooks, setPickerBooks] = useState([]);
  const [liked, setLiked] = useState([]);
  const [coldStartResults, setColdStartResults] = useState(null);
  const [coldStartLoading, setColdStartLoading] = useState(false);

  const search = async (q) => {
    setLoading(true);
    try {
      const { data } = await api.get("/books", { params: { q, page_size: 24 } });
      setBooks(data.books);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    search("");
  }, []);

  useEffect(() => {
    // seed a small picker grid for the "pick books you like" cold-start flow
    api.get("/books", { params: { page_size: 12 } }).then(({ data }) => setPickerBooks(data.books));
  }, []);

  const onSearchSubmit = (e) => {
    e.preventDefault();
    search(query);
  };

  const toggleLike = (bookId) => {
    setLiked((prev) => (prev.includes(bookId) ? prev.filter((id) => id !== bookId) : [...prev, bookId]));
  };

  const runColdStart = async () => {
    setColdStartLoading(true);
    try {
      const { data } = await api.post("/recommendations/cold-start", {
        liked_book_ids: liked,
        top_n: 10,
      });
      setColdStartResults(data.results);
    } finally {
      setColdStartLoading(false);
    }
  };

  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-3xl font-display font-semibold mb-1">Find your next read</h1>
        <p className="text-ink/60 mb-5">Search the catalog, or pick a few favorites below to get instant picks.</p>
        <form onSubmit={onSearchSubmit} className="flex gap-2 max-w-lg">
          <input
            className="flex-1 border border-rule rounded-lg px-3 py-2 bg-white/60 focus:outline-none focus:ring-2 focus:ring-gold"
            placeholder="Search by title..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="px-4 py-2 rounded-lg bg-forest text-paper font-medium hover:bg-forestlight transition-colors">
            Search
          </button>
        </form>
      </section>

      {!user && (
        <section className="border border-rule rounded-xl p-5 bg-white/40">
          <h2 className="font-display text-xl font-semibold mb-1">New here? Pick a few books you like</h2>
          <p className="text-sm text-ink/60 mb-4">
            No account needed -- this uses content-based similarity to suggest books right away.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mb-4">
            {pickerBooks.map((b) => (
              <button
                key={b.book_id}
                onClick={() => toggleLike(b.book_id)}
                className={`text-left p-2 rounded-lg border transition-colors ${
                  liked.includes(b.book_id) ? "border-gold bg-goldsoft/40" : "border-rule hover:border-gold"
                }`}
              >
                <p className="text-sm font-medium truncate">{b.title}</p>
                <p className="text-xs text-ink/50 truncate">{(b.authors || []).join(", ")}</p>
              </button>
            ))}
          </div>
          <button
            onClick={runColdStart}
            disabled={liked.length === 0 || coldStartLoading}
            className="px-4 py-2 rounded-lg bg-gold text-ink font-medium disabled:opacity-40 hover:bg-goldsoft transition-colors"
          >
            {coldStartLoading ? "Finding books..." : `Get picks from ${liked.length} book(s)`}
          </button>

          {coldStartResults && (
            <div className="grid sm:grid-cols-2 gap-3 mt-5">
              {coldStartResults.map((b) => (
                <BookCard key={b.book_id} book={b} />
              ))}
            </div>
          )}
        </section>
      )}

      <section>
        <h2 className="font-display text-xl font-semibold mb-3">
          {query ? `Results for "${query}"` : "Popular in the catalog"}
        </h2>
        {loading ? (
          <p className="text-ink/50">Loading...</p>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3">
            {books.map((b) => (
              <BookCard key={b.book_id} book={b} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
