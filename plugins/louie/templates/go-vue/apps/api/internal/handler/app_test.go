package handler

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// build writes an app's build into a temp dir: index.html and one asset.
func build(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(dir, "assets"), 0o755); err != nil {
		t.Fatalf("make assets: %v", err)
	}
	for name, body := range map[string]string{
		"index.html":       "<!doctype html><title>app</title>",
		"assets/index.js":  "console.log(1)",
		"assets/index.css": "body{}",
	} {
		if err := os.WriteFile(filepath.Join(dir, filepath.FromSlash(name)), []byte(body), 0o644); err != nil {
			t.Fatalf("write %s: %v", name, err)
		}
	}
	return dir
}

// serve sends h a request with the method to the path and returns what h answered.
func serve(t *testing.T, h http.Handler, method, path string) *httptest.ResponseRecorder {
	t.Helper()
	w := httptest.NewRecorder()
	h.ServeHTTP(w, httptest.NewRequest(method, path, nil))
	return w
}

func TestWithApp_ServesTheAppOnEveryPathButTheAPIs(t *testing.T) {
	h := WithApp(Routes(), build(t))
	for _, tc := range []struct {
		path, body, cache string
	}{
		{"/", "<title>app</title>", "no-cache"},
		{"/notes/1", "<title>app</title>", "no-cache"},
		{"/api/up", `"status":"up"`, ""},
	} {
		t.Run(tc.path, func(t *testing.T) {
			w := serve(t, h, http.MethodGet, tc.path)
			if w.Code != http.StatusOK {
				t.Fatalf("GET %s status = %d, want %d", tc.path, w.Code, http.StatusOK)
			}
			if !strings.Contains(w.Body.String(), tc.body) {
				t.Fatalf("GET %s body = %q, want it to contain %q", tc.path, w.Body.String(), tc.body)
			}
			if got := w.Header().Get("Cache-Control"); tc.cache != "" && got != tc.cache {
				t.Fatalf("GET %s Cache-Control = %q, want %q", tc.path, got, tc.cache)
			}
		})
	}
}

func TestWithApp_KeepsAssetsAYear(t *testing.T) {
	w := serve(t, WithApp(Routes(), build(t)), http.MethodGet, "/assets/index.js")
	if w.Code != http.StatusOK || w.Body.String() != "console.log(1)" {
		t.Fatalf("GET an asset = %d %q, want %d %q", w.Code, w.Body.String(), http.StatusOK, "console.log(1)")
	}
	if got, want := w.Header().Get("Cache-Control"), "public, max-age=31536000, immutable"; got != want {
		t.Fatalf("an asset's Cache-Control = %q, want %q", got, want)
	}
}

func TestWithApp_MissingAssetIs404(t *testing.T) {
	w := serve(t, WithApp(Routes(), build(t)), http.MethodGet, "/assets/missing.js")
	if w.Code != http.StatusNotFound {
		t.Fatalf("GET a missing asset status = %d, want %d", w.Code, http.StatusNotFound)
	}
}
