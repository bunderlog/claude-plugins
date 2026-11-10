// Package respond writes the API's JSON responses: a body, or an error with a stable machine code
// and a message for people.
package respond

import (
	"encoding/json"
	"log/slog"
	"net/http"
)

// JSON writes v as the response body with the status.
func JSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		slog.Warn("write response failed", "err", err)
	}
}

// Error writes {"code": code, "message": message} with the status.
func Error(w http.ResponseWriter, status int, code, message string) {
	JSON(w, status, errorBody{Code: code, Message: message})
}

// Internal logs err and writes a generic 500, never err's detail.
func Internal(w http.ResponseWriter, r *http.Request, err error) {
	slog.ErrorContext(r.Context(), "request failed", "method", r.Method, "path", r.URL.Path, "err", err)
	Error(w, http.StatusInternalServerError, "internal", "Something went wrong on our side.")
}

type errorBody struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}
