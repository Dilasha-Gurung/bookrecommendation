import React from "react";
import { Link } from "react-router-dom";

export default function BookCard({ book }) {
  return (
    <Link
      to={`/books/${book.book_id}`}
      className="group flex gap-4 p-3 rounded-lg border border-rule hover:border-gold hover:shadow-sm transition-all bg-white/40"
    >
      <div className="w-1 self-stretch rounded-full spine flex-shrink-0" />
      {book.image_url ? (
        <img
          src={book.image_url}
          alt={book.title}
          className="w-14 h-20 object-cover rounded shadow-sm flex-shrink-0"
        />
      ) : (
        <div className="w-14 h-20 rounded bg-goldsoft flex-shrink-0" />
      )}
      <div className="min-w-0 flex-1">
        <h3 className="font-display font-semibold leading-snug truncate group-hover:text-forest">
          {book.title}
        </h3>
        <p className="text-sm text-ink/60 truncate">
          {(book.authors || []).join(", ")}
        </p>
        <div className="mt-1 flex items-center gap-2 text-xs text-ink/50">
          {book.average_rating != null && <span>★ {book.average_rating.toFixed(2)}</span>}
          {book.pdf_available ? (
            <span className="text-forest">PDF available</span>
          ) : (
            <span>No PDF</span>
          )}
        </div>
      </div>
    </Link>
  );
}
