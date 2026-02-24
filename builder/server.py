"""Development server: serve, watch, and dev (with LiveReload)."""

import os
import hashlib
from pathlib import Path

from builder import PROJECT_ROOT
from builder.site import SiteBuilder


def serve(port=8000):
    import http.server
    import socketserver

    os.chdir(PROJECT_ROOT / "dist")
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"==> Serving at http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n==> Server stopped.")


def watch():
    import time
    builder = SiteBuilder()
    builder.build()

    docs_dir = PROJECT_ROOT / "docs"
    templates_dir = PROJECT_ROOT / "templates"
    static_dir = PROJECT_ROOT / "static"
    config_file = PROJECT_ROOT / "config.json"

    last_hash = _compute_watch_hash(docs_dir, templates_dir, static_dir, config_file)

    print("==> Watching for changes ... (Ctrl+C to stop)")
    while True:
        time.sleep(1)
        current = _compute_watch_hash(docs_dir, templates_dir, static_dir, config_file)
        if current != last_hash:
            print("==> Change detected, rebuilding ...")
            builder.build()
            last_hash = current


def _compute_watch_hash(docs_dir: Path, templates_dir: Path, static_dir: Path, config_file: Path) -> str:
    """Compute hash of all watched files."""
    h = hashlib.md5()

    # Hash docs
    for f in sorted(docs_dir.rglob("*.md")):
        h.update(f.read_bytes())
        h.update(str(f.stat().st_mtime).encode())

    # Hash templates
    if templates_dir.exists():
        for f in sorted(templates_dir.rglob("*.html")):
            h.update(f.read_bytes())
            h.update(str(f.stat().st_mtime).encode())

    # Hash static files
    if static_dir.exists():
        for f in sorted(static_dir.rglob("*")):
            if f.is_file():
                h.update(f.read_bytes())
                h.update(str(f.stat().st_mtime).encode())

    # Hash config
    if config_file.exists():
        h.update(config_file.read_bytes())
        h.update(str(config_file.stat().st_mtime).encode())

    return h.hexdigest()


def dev(port=8000):
    """Run development server with auto-rebuild and live reload."""
    import threading
    import time
    import http.server
    import socketserver

    builder = SiteBuilder()

    # Inject live reload script into templates during dev mode
    def inject_livereload(html: str) -> str:
        reload_script = '''
<script>
(function() {
  let lastCheck = Date.now();
  setInterval(() => {
    fetch('/livereload-check?' + lastCheck)
      .then(res => res.text())
      .then(data => {
        if (data === 'reload') {
          console.log('[LiveReload] Reloading...');
          location.reload();
        }
        lastCheck = Date.now();
      })
      .catch(() => {});
  }, 1000);
})();
</script>
</body>'''
        return html.replace('</body>', reload_script)

    # Custom handler with live reload endpoint
    class LiveReloadHandler(http.server.SimpleHTTPRequestHandler):
        last_build_time = time.time()

        def do_GET(self):
            if self.path.startswith('/livereload-check'):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                query_time = float(self.path.split('?')[1]) / 1000 if '?' in self.path else 0
                if LiveReloadHandler.last_build_time > query_time:
                    self.wfile.write(b'reload')
                else:
                    self.wfile.write(b'ok')
            else:
                super().do_GET()

    # Initial build with livereload injection
    builder.build()
    for html_file in builder.dist_dir.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        html_file.write_text(inject_livereload(content), encoding="utf-8")

    # Start file watcher in background thread
    docs_dir = PROJECT_ROOT / "docs"
    templates_dir = PROJECT_ROOT / "templates"
    static_dir = PROJECT_ROOT / "static"
    config_file = PROJECT_ROOT / "config.json"

    last_hash = _compute_watch_hash(docs_dir, templates_dir, static_dir, config_file)

    def watch_files():
        nonlocal last_hash
        while True:
            time.sleep(1)
            current = _compute_watch_hash(docs_dir, templates_dir, static_dir, config_file)
            if current != last_hash:
                print("==> Change detected, rebuilding ...")
                builder.build()
                # Re-inject livereload script
                for html_file in builder.dist_dir.rglob("*.html"):
                    content = html_file.read_text(encoding="utf-8")
                    html_file.write_text(inject_livereload(content), encoding="utf-8")
                LiveReloadHandler.last_build_time = time.time()
                last_hash = current

    watcher_thread = threading.Thread(target=watch_files, daemon=True)
    watcher_thread.start()

    # Start HTTP server
    os.chdir(builder.dist_dir)
    with socketserver.TCPServer(("", port), LiveReloadHandler) as httpd:
        print(f"==> Dev server running at http://localhost:{port}")
        print("==> Watching for changes with live reload enabled...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n==> Server stopped.")
