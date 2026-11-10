// Command server serves the API, and the app's build where APP_DIR names it, on one port (ADR
// stack). It reads the database's address from DATABASE_URL, runs the migrations it hasn't run
// yet, listens on ADDR (default :8080) and stops on SIGINT or SIGTERM, letting the requests it is
// serving finish.
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/__OWNER__/__NAME__/internal/database"
	"github.com/__OWNER__/__NAME__/internal/handler"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	url := os.Getenv("DATABASE_URL")
	if url == "" {
		slog.ErrorContext(ctx, "DATABASE_URL is unset; `mise run dev` sets it")
		os.Exit(2)
	}
	routes := handler.Routes()
	if dir := os.Getenv("APP_DIR"); dir != "" {
		index := filepath.Join(dir, "index.html")
		if _, err := os.Stat(index); err != nil {
			slog.ErrorContext(ctx, "APP_DIR holds no app's build", "app_dir", dir, "err", err)
			os.Exit(2)
		}
		routes = handler.WithApp(routes, dir)
	}

	pool, err := database.Open(ctx, url)
	if err != nil {
		slog.ErrorContext(ctx, "open the database failed", "err", err)
		os.Exit(1)
	}
	defer pool.Close()

	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	srv := &http.Server{
		Addr:              addr,
		Handler:           routes,
		ReadHeaderTimeout: 10 * time.Second,
	}

	served := make(chan error, 1)
	go func() {
		slog.InfoContext(ctx, "serving", "addr", addr)
		served <- srv.ListenAndServe()
	}()

	select {
	case err := <-served:
		if !errors.Is(err, http.ErrServerClosed) {
			slog.ErrorContext(ctx, "serve failed", "addr", addr, "err", err)
			os.Exit(1)
		}
	case <-ctx.Done():
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if err := srv.Shutdown(shutdownCtx); err != nil {
			slog.ErrorContext(shutdownCtx, "shutdown failed", "err", err)
			os.Exit(1)
		}
	}
}
