"""XPathGenie — Flask API + static file server."""

from flask import Flask, request, jsonify, send_from_directory
from urllib.parse import urlparse
import os
import time

from genie.fetcher import fetch_all
from genie.compressor import compress
from genie.analyzer import analyze
from genie.validator import validate

app = Flask(__name__, static_folder="static", static_url_path="/static")


@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json()
    if not data or "urls" not in data:
        return jsonify({"error": "urls required"}), 400

    urls = [u.strip() for u in data["urls"] if u.strip()]
    if not urls:
        return jsonify({"error": "No valid URLs"}), 400
    if len(urls) > 10:
        return jsonify({"error": "Max 10 URLs"}), 400

    t0 = time.time()

    # 1. Fetch
    pages = fetch_all(urls)
    fetched = [p for p in pages if p["html"]]
    if not fetched:
        return jsonify({"error": "Failed to fetch all URLs", "details": [p["error"] for p in pages]}), 400

    # 2. Compress
    compressed = []
    for p in fetched:
        c = compress(p["html"])
        compressed.append(c)

    # 3. Analyze with Gemini
    try:
        result = analyze(compressed)
    except Exception as e:
        return jsonify({"error": f"AI analysis failed: {e}"}), 500

    # 4. Validate
    validated = validate(result["mappings"], pages)

    # Build response
    site = urlparse(urls[0]).netloc
    elapsed = round(time.time() - t0, 1)

    return jsonify({
        "site": site,
        "mappings": validated,
        "pages_analyzed": len(fetched),
        "pages_failed": len(pages) - len(fetched),
        "tokens_used": result.get("tokens_used", 0),
        "elapsed_seconds": elapsed,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8789, threaded=True, debug=False)
