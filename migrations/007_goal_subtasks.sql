-- Checklist items on an external task. The client owns the list.
ALTER TABLE manon_goals ADD COLUMN IF NOT EXISTS subtasks JSONB NOT NULL DEFAULT '[]'::jsonb;
