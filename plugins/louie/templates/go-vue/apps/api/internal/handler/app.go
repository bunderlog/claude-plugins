package handler

import (
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strings"
)

// WithApp serves the app, apps/app's build in dir, beside the API on one port (ADR stack): /api/
// goes to api, a file the build holds is served as is, a missing asset is a 404, and any other
// path gets index.html, for the app's router to show. Files under /assets/ are named by their
// content's hash, so a browser keeps them a year; index.html is asked for again each time, so a
// deploy shows at once.
func WithApp(api http.Handler, dir string) http.Handler {
	files := http.FileServer(http.Dir(dir))
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		p := path.Clean("/" + r.URL.Path)
		switch {
		case strings.HasPrefix(p, "/api/"):
			api.ServeHTTP(w, r)
		case p != "/" && isFile(filepath.Join(dir, filepath.FromSlash(p))):
			if strings.HasPrefix(p, "/assets/") {
				w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
			}
			files.ServeHTTP(w, r)
		case strings.HasPrefix(p, "/assets/"):
			http.NotFound(w, r)
		default:
			w.Header().Set("Cache-Control", "no-cache")
			http.ServeFile(w, r, filepath.Join(dir, "index.html"))
		}
	})
}

func isFile(name string) bool {
	fi, err := os.Stat(name)
	return err == nil && !fi.IsDir()
}
