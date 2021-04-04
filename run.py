import http.server
import os

PORT = 18080

web_dir = os.path.join(os.path.dirname(__file__), "dist")
os.chdir(web_dir)

Handler = http.server.SimpleHTTPRequestHandler

Handler.extensions_map = {
    "": "text/html",
    ".css": "text/css",
    ".json": "application/json",
    ".webmanifest": "application/json",
    ".js": "application/javascript",
    ".eot": "application/vnd.ms-fontobject",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}

httpd = http.server.HTTPServer(("", PORT), Handler)

print(f"serving at http://localhost:{PORT}")
httpd.serve_forever()
