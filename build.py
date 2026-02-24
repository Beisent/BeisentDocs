#!/usr/bin/env python3
"""BeisentDocs - Markdown to HTML documentation site generator.

Usage:
  python build.py               # Build site
  python build.py serve [port]  # Build and serve
  python build.py watch         # Watch mode (auto-rebuild)
  python build.py dev [port]    # Dev server with LiveReload
"""

import sys
from builder import SiteBuilder
from builder.server import serve, watch, dev

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        SiteBuilder().build()
        serve(port)
    elif len(sys.argv) > 1 and sys.argv[1] == "watch":
        watch()
    elif len(sys.argv) > 1 and sys.argv[1] == "dev":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        dev(port)
    else:
        SiteBuilder().build()
