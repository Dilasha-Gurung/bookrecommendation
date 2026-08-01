-- =====================================================================
-- Hybrid Book Recommender - MySQL schema (XAMPP / MySQL 5.7+ / 8.x)
-- =====================================================================
CREATE DATABASE IF NOT EXISTS book_recommender
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE book_recommender;

-- ---------------------------------------------------------------------
-- USERS
-- Dataset users (imported from ratings.csv) and real registered users
-- live in the same table. dataset_user_id links back to the original
-- ratings.csv user_id and is NULL for real users who register normally.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  dataset_user_id   BIGINT UNSIGNED NULL UNIQUE,
  username           VARCHAR(64)  NOT NULL UNIQUE,
  email              VARCHAR(190) NULL UNIQUE,
  password_hash      VARCHAR(255) NOT NULL,
  is_dataset_user    TINYINT(1)   NOT NULL DEFAULT 0,
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- BOOKS
-- book_id is preserved exactly as it appears in books_enriched.csv /
-- ratings.csv -- it is NOT auto-generated and NOT re-mapped.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS books (
  book_id              INT UNSIGNED PRIMARY KEY,
  isbn                 VARCHAR(20)  NULL,
  isbn13               VARCHAR(20)  NULL,
  title                VARCHAR(500) NOT NULL,
  original_title       VARCHAR(500) NULL,
  authors              TEXT NULL,          -- JSON array string, e.g. ["Suzanne Collins"]
  authors_2            TEXT NULL,          -- secondary/cleaned authors field, same JSON-array format
  description          MEDIUMTEXT NULL,
  genres               TEXT NULL,          -- JSON array string, e.g. ["fantasy","fiction"]
  publication_year     INT NULL,
  pages                INT NULL,
  language_code        VARCHAR(10) NULL,
  average_rating       DECIMAL(3,2) NULL,
  ratings_count        INT UNSIGNED NULL,
  image_url            VARCHAR(500) NULL,
  created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FULLTEXT KEY ft_title (title)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- RATINGS
-- ratings.csv's user_id refers to users.dataset_user_id, NOT users.id.
-- The import script resolves dataset_user_id -> users.id before insert,
-- so this table always stores the internal users.id.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ratings (
  rating_id   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     BIGINT UNSIGNED NOT NULL,
  book_id     INT UNSIGNED NOT NULL,
  rating      TINYINT UNSIGNED NOT NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ratings_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_ratings_book FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
  CONSTRAINT chk_rating_range CHECK (rating BETWEEN 1 AND 5),
  UNIQUE KEY uq_user_book (user_id, book_id),
  KEY idx_ratings_user (user_id),
  KEY idx_ratings_book (book_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- PDF_FILES
-- Only metadata/path lives in MySQL. Actual PDF bytes live on disk
-- under project/pdfs/. Not every book has a row here.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pdf_files (
  pdf_id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  book_id     INT UNSIGNED NOT NULL UNIQUE,
  file_path   VARCHAR(500) NOT NULL,   -- relative path under pdfs/, e.g. "1.pdf"
  uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pdf_book FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE
) ENGINE=InnoDB;
