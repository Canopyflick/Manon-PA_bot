-- Urgency stays until it is turned off. A stored date meant "urgent on that day".
-- Any date still present was never manually cleared, so it becomes urgent = true.

ALTER TABLE manon_goals ADD COLUMN IF NOT EXISTS urgent BOOLEAN NOT NULL DEFAULT false;

UPDATE manon_goals
SET urgent = true
WHERE urgent_on IS NOT NULL;

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
                'urgent', NEW.urgent,
                'description', NEW.goal_description
            )
        );
        IF NEW.urgent THEN
            INSERT INTO goal_events (goal_id, event_type, actor, payload)
            VALUES (
                NEW.goal_id,
                'urgent_set',
                actor_name,
                jsonb_build_object('urgent', true)
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

    IF NEW.urgent IS DISTINCT FROM OLD.urgent THEN
        INSERT INTO goal_events (goal_id, event_type, actor, payload)
        VALUES (
            NEW.goal_id,
            CASE WHEN NEW.urgent THEN 'urgent_set' ELSE 'urgent_cleared' END,
            actor_name,
            jsonb_build_object('urgent', NEW.urgent)
        );
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

ALTER TABLE manon_goals DROP COLUMN IF EXISTS urgent_on;
