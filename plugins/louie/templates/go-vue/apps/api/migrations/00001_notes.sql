-- An example to replace with the product's first real migration before its first deploy (ADR
-- stack).

-- +goose Up
CREATE TABLE notes (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    body text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- +goose Down
DROP TABLE notes;
