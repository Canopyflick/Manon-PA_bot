-- Reading/watch-later items. item_id is the #N shown in chat, separate from goal ids.
CREATE TABLE IF NOT EXISTS manon_library (
    item_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    note TEXT,
    priority TEXT NOT NULL DEFAULT 'maybe' CHECK (priority IN ('must_read', 'maybe')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'read', 'archived')),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    FOREIGN KEY (user_id, chat_id) REFERENCES manon_users (user_id, chat_id),
    UNIQUE (user_id, chat_id, url)
);

CREATE INDEX IF NOT EXISTS idx_manon_library_user_chat_status
    ON manon_library (user_id, chat_id, status);
