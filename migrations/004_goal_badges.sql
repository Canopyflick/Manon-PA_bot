-- Badges chosen in external apps (benwerktijd). 'recurring' is recreated by the client on completion.
ALTER TABLE manon_goals ADD COLUMN IF NOT EXISTS badges TEXT[] NOT NULL DEFAULT '{}';
