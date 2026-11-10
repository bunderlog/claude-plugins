-- An example to replace with the product's own queries (ADR stack).

-- name: ListNotes :many
SELECT id, body, created_at
FROM notes
ORDER BY created_at;
