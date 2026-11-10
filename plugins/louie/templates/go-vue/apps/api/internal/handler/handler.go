// Package handler serves the API's routes.
package handler

import (
	"net/http"

	"github.com/__OWNER__/__NAME__/internal/respond"
)

// Routes is the API's every route.
func Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/up", NewUpHandler().Up)
	return mux
}

// UpHandler says the server is up. It touches no database, so it answers whatever Postgres is
// doing (ADR stack).
type UpHandler struct{}

// NewUpHandler builds an UpHandler.
func NewUpHandler() *UpHandler {
	return &UpHandler{}
}

type upResponse struct {
	Status string `json:"status"`
}

// Up answers 200 with {"status": "up"}.
func (h *UpHandler) Up(w http.ResponseWriter, _ *http.Request) {
	respond.JSON(w, http.StatusOK, upResponse{Status: "up"})
}
