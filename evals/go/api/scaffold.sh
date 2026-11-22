#!/bin/bash
# A small Go 1.27 service with a store and a response helper but no routes yet: Go 1.22's ServeMux
# routes by method and path wildcard, and Go 1.27 ships a `uuid` package, so neither needs a
# dependency, and the module declares none.
set -euo pipefail
git init -q -b main
mkdir -p cmd/api internal/store internal/respond
cat > go.mod <<'R'
module example.com/monitor

go 1.27
R
cat > cmd/api/main.go <<'R'
// Command api serves the monitor service's HTTP API.
package main

import (
	"log/slog"
	"net/http"
	"os"

	"example.com/monitor/internal/store"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stderr, nil))
	monitors := store.NewMemory()
	_ = monitors

	srv := &http.Server{Addr: ":8080"}
	logger.Info("listening", "addr", srv.Addr)
	if err := srv.ListenAndServe(); err != nil {
		logger.Error("server stopped", "err", err)
		os.Exit(1)
	}
}
R
cat > internal/store/monitors.go <<'R'
// Package store keeps the service's monitors.
package store

import (
	"context"
	"errors"
	"sync"
	"time"
)

// ErrNotFound is returned when no monitor has the id asked for.
var ErrNotFound = errors.New("monitor not found")

// Monitor is a URL the service checks.
type Monitor struct {
	ID        string
	URL       string
	CreatedAt time.Time
}

// Memory keeps monitors in memory.
type Memory struct {
	mu       sync.Mutex
	monitors map[string]Monitor
}

// NewMemory returns an empty store.
func NewMemory() *Memory {
	return &Memory{monitors: map[string]Monitor{}}
}

// Create stores m under its ID.
func (s *Memory) Create(ctx context.Context, m Monitor) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.monitors[m.ID] = m
	return nil
}

// Get returns the monitor with the id, or ErrNotFound.
func (s *Memory) Get(ctx context.Context, id string) (Monitor, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	m, ok := s.monitors[id]
	if !ok {
		return Monitor{}, ErrNotFound
	}
	return m, nil
}
R
cat > internal/respond/respond.go <<'R'
// Package respond writes the service's HTTP responses.
package respond

import (
	"encoding/json"
	"net/http"
)

// JSON writes v as the JSON body with the status.
func JSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// Error writes an error body: a stable machine code and a message for people.
func Error(w http.ResponseWriter, status int, code, message string) {
	JSON(w, status, map[string]string{"code": code, "message": message})
}
R
git add -A
git -c user.name=dev -c user.email=dev@example.com commit -q -m "Start the monitor service"
