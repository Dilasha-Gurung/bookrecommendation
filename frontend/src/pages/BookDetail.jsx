import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../api.js";
import BookCard from "../components/BookCard.jsx";

export default function BookDetail() {
  const { bookId } = useParams();
  const [book, setBook] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [pdfStatus, setPdfStatus] = useState(null);

  useEffect(() => {
    api.get(`/books/${bookId}`).then(({ data }) => setBook(data));
    api.get(`/recommendations/similar/${bookId}`, { params: { top_n: 6 } }).then(({ data }) =>
      setSimilar(data.results)
    );
    api.get(`/pdf/${bookId}/status`).then(({ data }) => setPdfStatus(data.available));
  }, [bookId]);

  if (!book) return <p className="text-ink/50">Loading...</p>;

  return (
    <div className="space-y-10">
      <section className="flex gap-6">
        {book.image_url ? (
          <img src={book.image_url} alt={book.title} className="w-40 h-56 object-cover rounded-lg shadow" />
        ) : (
          <div className="w-40 h-56 rounded-lg bg-goldsoft flex-shrink-0" />
        )}
        <div className="min-w-0">
          <h1 className="text-3xl font-display font-semibold">{book.title}</h1>
          <p className="text-ink/60 mt-1">{(book.authors || []).join(", ")}</p>
          <div className="flex flex-wrap gap-2 mt-3">
            {(book.genres || []).map((g) => (
              <span key={g} className="text-xs px-2 py-1 rounded-full bg-goldsoft/50 text-ink/70">
                {g}
              </span>
            ))}
          </div>
          {book.average_rating != null && (
            <p className="mt-3 text-sm text-ink/70">★ {book.average_rating.toFixed(2)} ({book.ratings_count} ratings)</p>
          )}

          <div className="mt-5">
            {pdfStatus === null ? null : pdfStatus ? (
              <a
                href={`/api/pdf/${bookId}`}
                target="_blank"
                rel="noreferrer"
                className="inline-block px-4 py-2 rounded-lg bg-forest text-paper font-medium hover:bg-forestlight transition-colors"
              >
                Read PDF
              </a>
            ) : (
              <span className="inline-block px-4 py-2 rounded-lg bg-rule/40 text-ink/50 text-sm">
                PDF unavailable for this book
              </span>
            )}
          </div>

          {book.description && (
            <p className="mt-5 text-sm leading-relaxed text-ink/80 max-w-2xl">{book.description}</p>
          )}
        </div>
      </section>

      <section>
        <h2 className="font-display text-xl font-semibold mb-3">Similar books</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          {similar.map((b) => (
            <BookCard key={b.book_id} book={b} />
          ))}
        </div>
      </section>
    </div>
  );
}
