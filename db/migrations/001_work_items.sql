-- Work items for the Session 2 dry run. Idempotent: safe to run repeatedly.
CREATE TABLE IF NOT EXISTS work_items (
    id          BIGSERIAL PRIMARY KEY,
    title       TEXT        NOT NULL CHECK (length(trim(title)) > 0),
    description TEXT        NOT NULL DEFAULT '',
    done        BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    done_at     TIMESTAMPTZ
);
