-- Shared goal sources. Existing rows stay source = 'manon'.
-- External apps (benwerktijd, later others) write through the goals API.

CREATE TABLE IF NOT EXISTS goal_sources (
    source TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    api_writable BOOLEAN NOT NULL DEFAULT false
);

INSERT INTO goal_sources (source, label, api_writable) VALUES
    ('manon', 'Manon', false),
    ('benwerktijd', 'benwerktijd', true)
ON CONFLICT (source) DO UPDATE
    SET label = EXCLUDED.label,
        api_writable = EXCLUDED.api_writable;

ALTER TABLE manon_goals ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manon';
ALTER TABLE manon_goals ADD COLUMN IF NOT EXISTS external_id TEXT;
ALTER TABLE manon_goals ADD COLUMN IF NOT EXISTS urgent_on DATE;
ALTER TABLE manon_goals ADD COLUMN IF NOT EXISTS sort_order DOUBLE PRECISION;
ALTER TABLE manon_goals ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
ALTER TABLE manon_goals ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

UPDATE manon_goals
SET created_at = COALESCE(created_at, set_time, NOW())
WHERE created_at IS NULL;

UPDATE manon_goals
SET updated_at = COALESCE(updated_at, completion_time, set_time, NOW())
WHERE updated_at IS NULL;

ALTER TABLE manon_goals ALTER COLUMN created_at SET DEFAULT NOW();
ALTER TABLE manon_goals ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE manon_goals ALTER COLUMN updated_at SET DEFAULT NOW();
ALTER TABLE manon_goals ALTER COLUMN updated_at SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'manon_goals_source_fkey'
    ) THEN
        ALTER TABLE manon_goals
            ADD CONSTRAINT manon_goals_source_fkey
            FOREIGN KEY (source) REFERENCES goal_sources (source);
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS manon_goals_source_external_id_idx
    ON manon_goals (source, external_id)
    WHERE external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS manon_goals_user_source_status_idx
    ON manon_goals (user_id, source, status);

ALTER TABLE manon_users ADD COLUMN IF NOT EXISTS auth_user_id UUID;

CREATE UNIQUE INDEX IF NOT EXISTS manon_users_auth_user_id_idx
    ON manon_users (auth_user_id)
    WHERE auth_user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS goal_events (
    event_id BIGSERIAL PRIMARY KEY,
    goal_id INT NOT NULL REFERENCES manon_goals (goal_id),
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    payload JSONB,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS goal_events_goal_id_idx ON goal_events (goal_id, occurred_at);

CREATE OR REPLACE FUNCTION manon_goals_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $updated$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$updated$;

CREATE OR REPLACE FUNCTION manon_goals_log_event()
RETURNS trigger
LANGUAGE plpgsql
AS $log$
DECLARE
    actor_name TEXT;
    evt TEXT;
BEGIN
    actor_name := current_setting('app.actor', true);
    IF actor_name IS NULL OR btrim(actor_name) = '' THEN
        actor_name := 'manon';
    END IF;

    IF TG_OP = 'INSERT' THEN
        INSERT INTO goal_events (goal_id, event_type, actor, payload)
        VALUES (
            NEW.goal_id,
            'created',
            actor_name,
            jsonb_build_object(
                'status', NEW.status,
                'source', NEW.source,
                'urgent_on', NEW.urgent_on,
                'description', NEW.goal_description
            )
        );
        IF NEW.urgent_on IS NOT NULL THEN
            INSERT INTO goal_events (goal_id, event_type, actor, payload)
            VALUES (
                NEW.goal_id,
                'urgent_set',
                actor_name,
                jsonb_build_object('urgent_on', NEW.urgent_on)
            );
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.status IS DISTINCT FROM OLD.status THEN
        evt := CASE
            WHEN NEW.status = 'archived_done' THEN 'completed'
            WHEN NEW.status = 'archived_canceled' THEN 'canceled'
            WHEN NEW.status = 'archived_failed' THEN 'failed'
            WHEN OLD.status IN ('archived_done', 'archived_failed', 'archived_canceled')
                 AND NEW.status IN ('prepared', 'pending', 'paused', 'limbo') THEN 'reopened'
            ELSE 'status_changed'
        END;
        INSERT INTO goal_events (goal_id, event_type, actor, payload)
        VALUES (
            NEW.goal_id,
            evt,
            actor_name,
            jsonb_build_object('from', OLD.status, 'to', NEW.status)
        );
    END IF;

    IF NEW.urgent_on IS DISTINCT FROM OLD.urgent_on THEN
        IF NEW.urgent_on IS NULL THEN
            INSERT INTO goal_events (goal_id, event_type, actor, payload)
            VALUES (
                NEW.goal_id,
                'urgent_cleared',
                actor_name,
                jsonb_build_object('urgent_on', OLD.urgent_on)
            );
        ELSE
            INSERT INTO goal_events (goal_id, event_type, actor, payload)
            VALUES (
                NEW.goal_id,
                'urgent_set',
                actor_name,
                jsonb_build_object('urgent_on', NEW.urgent_on)
            );
        END IF;
    END IF;

    IF NEW.goal_description IS DISTINCT FROM OLD.goal_description THEN
        INSERT INTO goal_events (goal_id, event_type, actor, payload)
        VALUES (
            NEW.goal_id,
            'edited',
            actor_name,
            jsonb_build_object('from', OLD.goal_description, 'to', NEW.goal_description)
        );
    END IF;

    RETURN NEW;
END;
$log$;

DROP TRIGGER IF EXISTS manon_goals_set_updated_at ON manon_goals;
CREATE TRIGGER manon_goals_set_updated_at
    BEFORE UPDATE ON manon_goals
    FOR EACH ROW
    EXECUTE FUNCTION manon_goals_set_updated_at();

DROP TRIGGER IF EXISTS manon_goals_log_event ON manon_goals;
CREATE TRIGGER manon_goals_log_event
    AFTER INSERT OR UPDATE ON manon_goals
    FOR EACH ROW
    EXECUTE FUNCTION manon_goals_log_event();
