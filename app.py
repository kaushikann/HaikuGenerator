import os
import json
import urllib.request
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="public")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


@app.route("/")
def index():
    return send_from_directory("public", "index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "").strip()

    if not topic:
        return jsonify({"error": "No topic provided"}), 400

    try:
        haiku = call_openai(topic)
        return jsonify({"haiku": haiku})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def call_openai(topic):
    payload = json.dumps({
        "model": "gpt-4o",
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
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    text = result["choices"][0]["message"]["content"].strip()
    lines = [l.strip() for l in text.splitlines() if l.strip()][:3]
    if len(lines) < 3:
        raise ValueError("Could not parse three haiku lines from response")
    return lines


if __name__ == "__main__":
    app.run(port=5000, debug=True)
