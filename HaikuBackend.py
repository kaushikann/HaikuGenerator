import os
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

HTML_PAGE = open(os.path.join(os.path.dirname(__file__), "index.html")).read()


class HaikuHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode())

    def do_POST(self):
        if self.path != "/generate":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body)
            topic = data.get("topic", "").strip()
            if not topic:
                raise ValueError("No topic provided")
        except Exception as e:
            self._json_error(400, str(e))
            return

        try:
            haiku = self._call_anthropic(topic)
            self._json_ok({"haiku": haiku})
        except Exception as e:
            self._json_error(500, str(e))

    def _call_anthropic(self, topic):
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
            "messages": [{
                "role": "user",
                "content": (
                    f'Write a haiku about: "{topic}". '
                    "Return ONLY the three lines of the haiku, one per line, "
                    "with no title, no explanation, no punctuation at the end "
                    "of lines, and nothing else. Strictly follow the 5-7-5 syllable structure."
                )
            }]
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())

        text = result["content"][0]["text"].strip()
        lines = [l.strip() for l in text.splitlines() if l.strip()][:3]
        if len(lines) < 3:
            raise ValueError("Could not parse three haiku lines from response")
        return lines

    def _json_ok(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_error(self, code, message):
        body = json.dumps({"error": message}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    if not ANTHROPIC_API_KEY:
        print("⚠️  Warning: ANTHROPIC_API_KEY is not set. Set it before running.")
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), HaikuHandler)
    print(f"🌿 Haiku Generator running at http://localhost:{port}")
    server.serve_forever()
