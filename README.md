# Hybrid Book Recommendation System

Content-based (TF-IDF + cosine similarity over `title + authors + genres +
description`) **+** collaborative filtering (item-based, adjusted cosine over
`ratings.csv`), blended into a hybrid score, served by a Flask + MySQL API,
with a React + Tailwind frontend and secure PDF delivery.

```
project/
├── backend/
│   ├── app.py                  Flask app entrypoint
│   ├── config.py                All settings (env-overridable)
│   ├── db.py                    MySQL connection helper
│   ├── requirements.txt
│   ├── .env.example
│   ├── routes/
│   │   ├── auth.py              register / login (JWT)
│   │   ├── books.py             list / search / detail
│   │   ├── recommendations.py   similar / for-you / cold-start
│   │   └── pdf.py                secure PDF serving
│   ├── services/
│   │   ├── content_recommender.py
│   │   ├── collaborative_recommender.py
│   │   └── hybrid_recommender.py
│   ├── scripts/
│   │   ├── schema.sql
│   │   ├── validate_data.py
│   │   ├── import_books.py
│   │   ├── import_users.py
│   │   ├── import_ratings.py
│   │   ├── build_content_model.py
│   │   └── build_collaborative_model.py
│   └── models/                  generated .pkl files (created by build scripts)
├── data/
│   ├── books_enriched.csv       <- put your CSV here
│   └── ratings.csv               <- put your CSV here
├── pdfs/                         <- put PDF files here, named e.g. 1.pdf
└── frontend/                     React + Vite + Tailwind
```

---

## 1. Database setup (XAMPP)

Start Apache + MySQL from the XAMPP control panel, then:

```bash
# Windows: C:\xampp\mysql\bin\mysql.exe -u root
mysql -u root < backend/scripts/schema.sql
```

This creates the `book_recommender` database and the `users`, `books`,
`ratings`, and `pdf_files` tables described below.

### Schema summary

- **users** — `id` (PK, auto), `dataset_user_id` (nullable, unique — links
  to the original `ratings.csv` `user_id`), `username`, `email`,
  `password_hash` (bcrypt), `is_dataset_user`.
- **books** — `book_id` is the *same* ID as in the CSVs (not
  re-generated). `authors` / `genres` are stored as JSON array strings.
- **ratings** — `(user_id, book_id)` unique; `user_id` here is always
  `users.id`, never the raw CSV `user_id` — see the mapping note below.
- **pdf_files** — `book_id` (unique FK) -> `file_path` (relative path under
  `pdfs/`). Not every book has a row here, and that's expected.

### `ratings.csv` user_id -> MySQL mapping (important)

`ratings.csv`'s `user_id` is **not** used as `users.id` directly. Instead:

1. `import_users.py` creates one row per unique `ratings.csv` user_id, storing
   that original value in `users.dataset_user_id` and generating a MySQL
   `users.id` via auto-increment.
2. `import_ratings.py` looks up `dataset_user_id -> users.id` and only ever
   inserts the resolved `users.id` into `ratings.user_id`.

This keeps "the dataset's notion of a user" cleanly separate from "a real
account in this app" — real users who register get `dataset_user_id = NULL`.

---

## 2. Backend setup

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # then edit DB_PASSWORD etc. if your XAMPP MySQL needs one
```

Put your CSVs in `data/`:

```
data/books_enriched.csv
data/ratings.csv
```

### 2a. Validate the raw data (recommended first step)

```bash
cd backend/scripts
python validate_data.py
```

Prints row counts, duplicate `book_id` / `(user_id, book_id)` pairs, missing
titles/descriptions/genres, and confirms `ratings.book_id` fully matches
`books.book_id`.

### 2b. Import into MySQL, in this order

```bash
python import_books.py      # books_enriched.csv -> books
python import_users.py      # unique ratings.csv user_id -> users (dataset accounts)
python import_ratings.py    # ratings.csv -> ratings (maps user_id via dataset_user_id)
```

All three are safe to re-run: `import_books.py` upserts, `import_users.py` /
`import_ratings.py` skip anything already present (`INSERT IGNORE` + unique
keys), so nothing gets duplicated.

`ratings.csv` can be millions of rows — `import_ratings.py` streams it in
chunks and commits per chunk. If it's still too slow for your machine, the
docstring at the top of that file explains a `LOAD DATA INFILE` alternative.

### 2c. Build the recommendation models

```bash
python build_content_model.py         # TF-IDF over title+authors+genres+description
python build_collaborative_model.py   # item-based CF similarity table
```

These write `.pkl` files into `backend/models/`, which `app.py` loads at
startup. Re-run them whenever the underlying data changes meaningfully
(new books imported, a lot of new ratings, etc.) — there's no need to
re-run them on every server restart otherwise.

### 2d. Add PDFs (optional, per book)

Drop files into `pdfs/`, e.g. `pdfs/1.pdf`, then register them:

```sql
INSERT INTO pdf_files (book_id, file_path) VALUES (1, '1.pdf');
```

(A small `register_pdfs.py` helper that scans a folder and inserts rows for
every `<book_id>.pdf` it finds is a natural next script if you want to
automate this — ask and it can be added.)

### 2e. Run the API

```bash
cd backend
python app.py
```

Serves on `http://localhost:5000`. Check `GET /api/health`.

---

## 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Serves on `http://localhost:5173` and proxies `/api/*` to the Flask backend
(see `vite.config.js`). Sign up, search books, open a book to see similar
titles and (if available) read its PDF, or visit **For you** once logged in
for hybrid recommendations.

---

## 4. How the recommenders work

**Content-based** (`services/content_recommender.py`)
TF-IDF vectorizes `title + authors×2 + genres×2 + description` (authors/
genres weighted higher since they're short but high-signal versus the much
longer description), then cosine similarity finds nearest books. Works with
zero rating history — this is what powers "similar books" and the
logged-out cold-start picker.

**Collaborative filtering** (`services/collaborative_recommender.py`)
Item-based CF with adjusted cosine similarity: each book's ratings are
mean-centered (so a generous rater and a harsh rater who like the same
books still register as similar), then books are compared to each other
rather than users to each other — cheaper to keep fresh (10k books vs 50k+
users) and easy to explain: *"readers who rated book A highly also rated
book B highly."* Only the top-K neighbors per book are kept, so scoring a
user is O(their ratings × K), not O(all books).

**Hybrid** (`services/hybrid_recommender.py`)
```
final_score = alpha * content_score_norm + (1 - alpha) * collaborative_score_norm
```
Both components are min-max normalized to [0, 1] over the current candidate
set before blending (their raw scales differ — cosine similarity vs. a
predicted 1-5 rating). `alpha` defaults to 0.5 and is exposed as a query
param (`?alpha=0.7`) / a slider in the **For you** page — 0.5 is a
reasonable starting point, not a tuned optimum; adjust it by eye or, for a
report, by holding out some ratings and comparing precision@k across a few
alpha values.

**Cold start**
- No ratings, no picks: `GET /api/books` popularity ranking (Bayesian
  average of `average_rating`/`ratings_count`, so a 5.0 from 2 raters
  doesn't outrank a 4.3 from 10,000).
- No ratings, but the user picked a few "books I like": pure content-based
  similarity to those picks (`POST /api/recommendations/cold-start`).
- Once real ratings exist: the full hybrid blend (`GET
  /api/recommendations/for-you`).

---

## 5. API summary

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/auth/register` | — | `{username, email, password}` |
| POST | `/api/auth/login` | — | `{username\|email, password}` |
| GET | `/api/books?q=&page=&page_size=` | — | search/list |
| GET | `/api/books/<book_id>` | — | detail + `pdf_available` |
| GET | `/api/recommendations/similar/<book_id>?top_n=&only_with_pdf=` | — | content-based |
| GET | `/api/recommendations/for-you?alpha=&top_n=&only_with_pdf=` | JWT | hybrid |
| POST | `/api/recommendations/cold-start` | — | `{liked_book_ids, top_n}` |
| GET | `/api/pdf/<book_id>` | optional | streams the PDF or a clear "unavailable" JSON |
| GET | `/api/pdf/<book_id>/status` | — | `{available: true/false}` |

PDF serving never accepts a raw file path from the client — only a numeric
`book_id`, resolved against `pdf_files` and checked to stay inside `pdfs/`.

---

## 6. What was intentionally left out / left simple

- No password reset / email verification flow (add if this goes beyond a
  BCA project demo).
- `import_ratings.py` uses `executemany`; for a truly huge `ratings.csv`
  (tens of millions of rows) switch to `LOAD DATA INFILE` as noted in that
  script's docstring.
- Collaborative model rebuilds are manual (`build_collaborative_model.py`),
  not triggered automatically after every new rating — fine for a project
  with periodic re-training; a cron job or admin "rebuild models" button is
  a reasonable next step for something closer to production.
