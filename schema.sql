-- users table for flaskapp.py (the app also runs this on startup)
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password        TEXT NOT NULL,          -- salted hash, never the plain password
    firstname       TEXT NOT NULL,
    lastname        TEXT NOT NULL,
    email           TEXT NOT NULL,
    address         TEXT NOT NULL,
    filename        TEXT,                   -- name of the uploaded file, e.g. Limerick.txt
    stored_filename TEXT,                   -- where it is saved: uploads/<username>.txt
    word_count      INTEGER,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);
