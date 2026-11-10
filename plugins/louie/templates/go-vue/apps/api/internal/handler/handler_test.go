package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestUp_Answers200(t *testing.T) {
	w := httptest.NewRecorder()
	Routes().ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/api/up", nil))
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
