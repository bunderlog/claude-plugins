package handler

import (
	"encoding/json"
	"net/http"
	"testing"
)

// errorReply is respond.Error's body, read back.
type errorReply struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

func TestUp_Answers200(t *testing.T) {
	w := serve(t, Routes(), http.MethodGet, "/api/up")
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusOK)
	}
	var got upResponse
	if err := json.NewDecoder(w.Body).Decode(&got); err != nil {
		t.Fatalf("decode body %q: %v", w.Body.String(), err)
	}
	if got.Status != "up" {
		t.Fatalf("status field = %q, want %q", got.Status, "up")
	}
}

func TestRoutes_UnknownPathIs404JSON(t *testing.T) {
	w := serve(t, Routes(), http.MethodGet, "/api/nope")
	if w.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusNotFound)
	}
	if got := w.Header().Get("Content-Type"); got != "application/json" {
		t.Fatalf("Content-Type = %q, want %q", got, "application/json")
	}
	var got errorReply
	if err := json.NewDecoder(w.Body).Decode(&got); err != nil {
		t.Fatalf("decode body %q: %v", w.Body.String(), err)
	}
	if got.Code != "not_found" || got.Message == "" {
		t.Fatalf("body = %+v, want code %q and a message", got, "not_found")
	}
}

func TestRoutes_WrongMethodIs405JSON(t *testing.T) {
	w := serve(t, Routes(), http.MethodPost, "/api/up")
	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusMethodNotAllowed)
	}
	if got, want := w.Header().Get("Allow"), "GET, HEAD"; got != want {
		t.Fatalf("Allow = %q, want %q", got, want)
	}
	if got := w.Header().Get("Content-Type"); got != "application/json" {
		t.Fatalf("Content-Type = %q, want %q", got, "application/json")
	}
	var got errorReply
	if err := json.NewDecoder(w.Body).Decode(&got); err != nil {
		t.Fatalf("decode body %q: %v", w.Body.String(), err)
	}
	if got.Code != "method_not_allowed" || got.Message == "" {
		t.Fatalf("body = %+v, want code %q and a message", got, "method_not_allowed")
	}
}
