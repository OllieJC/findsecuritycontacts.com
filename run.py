import http.server
import os

PORT = 18080

web_dir = os.path.join(os.path.dirname(__file__), "dist")
os.chdir(web_dir)


class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_my_headers()
        http.server.SimpleHTTPRequestHandler.end_headers(self)

    def send_my_headers(self):
        html_paths = ["/gen/", "/top/"]
        for hp in html_paths:
            if self.path.startswith(hp) and len(self.path) > len(hp):
                self.send_header("Content-Type", "text/html")


MyHTTPRequestHandler.extensions_map = {
    ".css": "text/css",
    ".json": "text/plain",
    ".webmanifest": "application/json",
    ".js": "application/javascript",
    ".eot": "application/vnd.ms-fontobject",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    "": "text/html",
}

httpd = http.server.HTTPServer(("", PORT), MyHTTPRequestHandler)

print(f"serving at http://localhost:{PORT}")
httpd.serve_forever()
