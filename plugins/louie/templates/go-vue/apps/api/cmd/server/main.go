// Command server serves the API. It listens on ADDR (default :8080) and stops on SIGINT or
// SIGTERM, letting the requests it is serving finish.
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/__OWNER__/__NAME__/internal/handler"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	srv := &http.Server{
		Addr:              addr,
		Handler:           handler.Routes(),
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
