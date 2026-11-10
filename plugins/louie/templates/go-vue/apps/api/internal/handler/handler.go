// Package handler serves the API's routes.
package handler

import (
	"net/http"

	"github.com/__OWNER__/__NAME__/internal/respond"
)

// Routes is the API's every route. A path none of them takes gets respond's JSON 404, and a method
// its path doesn't take respond's JSON 405, with the Allow header naming the methods it does.
func Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/up", NewUpHandler().Up)
	return unrouted{mux: mux}
}

// unrouted hands a request one of mux's routes takes to mux, and answers any other through respond
// in place of the mux's plain-text 404 or 405.
type unrouted struct {
	mux *http.ServeMux
}

func (u unrouted) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	h, pattern := u.mux.Handler(r)
	if pattern != "" {
		// Through the mux, not h, so the route reads its path's values with r.PathValue.
		u.mux.ServeHTTP(w, r)
		return
	}
	reply := &headerOnly{header: http.Header{}}
	h.ServeHTTP(reply, r)
	if reply.status == http.StatusMethodNotAllowed {
		w.Header().Set("Allow", reply.header.Get("Allow"))
		respond.Error(w, r, http.StatusMethodNotAllowed, "method_not_allowed", "This path doesn't take that method.")
		return
	}
	respond.Error(w, r, http.StatusNotFound, "not_found", "Nothing is at this path.")
}

// headerOnly keeps the header and the status a handler writes, and drops its body.
type headerOnly struct {
	header http.Header
	status int
}

func (h *headerOnly) Header() http.Header { return h.header }

func (h *headerOnly) WriteHeader(status int) { h.status = status }

func (h *headerOnly) Write(b []byte) (int, error) {
	if h.status == 0 {
		h.status = http.StatusOK
	}
	return len(b), nil
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
func (h *UpHandler) Up(w http.ResponseWriter, r *http.Request) {
	respond.JSON(w, r, http.StatusOK, upResponse{Status: "up"})
}
