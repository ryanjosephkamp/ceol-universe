"""Serves the local universe file with byte ranges and CORS on 127.0.0.1, so
the site's list download can be tried before the dataset is public
(site/README.md, "The list download").

    python3 tools/serve_range.py data/release/ceol-universe-v1.0/universe.parquet 8766

It answers only a range request for a path ending in /universe.parquet, as
the hub does for the download; a request without a range is refused, never
answered with the whole file.
"""
import http.server, os, re, sys

PATH, PORT = sys.argv[1], int(sys.argv[2])
SIZE = os.path.getsize(PATH)


class H(http.server.BaseHTTPRequestHandler):
    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Range")
        self.send_header("Access-Control-Expose-Headers", "Content-Range, Content-Length")

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self):
        m = re.fullmatch(r"bytes=(\d+)-(\d*)", self.headers.get("Range", ""))
        if not self.path.endswith("/universe.parquet") or not m:
            self.send_response(416 if m is None else 404)
            self.cors()
            self.end_headers()
            return
        start = int(m.group(1))
        end = min(int(m.group(2)) if m.group(2) else SIZE - 1, SIZE - 1)
        self.send_response(206)
        self.cors()
        self.send_header("Content-Range", f"bytes {start}-{end}/{SIZE}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        with open(PATH, "rb") as f:
            f.seek(start)
            self.wfile.write(f.read(end - start + 1))

    def log_message(self, *a):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
