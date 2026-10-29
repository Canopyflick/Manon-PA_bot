-- Day from which an external task becomes urgent. The client turns the
-- flag on once that day arrives; until then urgent stays false.
ALTER TABLE manon_goals ADD COLUMN IF NOT EXISTS urgent_on DATE;
