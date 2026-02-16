"""XPathGenie — Flask API + static file server."""

from flask import Flask, request, jsonify, send_from_directory
from urllib.parse import urlparse
import os
import time

from genie.fetcher import fetch_all
from genie.compressor import compress
from genie.analyzer import analyze, refine
from genie.validator import validate, find_multi_matches, narrow_by_first_match

app = Flask(__name__, static_folder="static", static_url_path="/static")


@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/api/fetch")
def api_fetch():
    """Fetch HTML for Aladdin page (server-side to avoid CORS)."""
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        pages = fetch_all([url])
        if pages and pages[0].get("html"):
            return jsonify({"html": pages[0]["html"], "url": url})
        return jsonify({"error": pages[0].get("error", "fetch failed")}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    wantlist = data.get("wantlist")  # optional: {"field": "", ...}
    try:
        result = analyze(compressed, wantlist=wantlist)
    except Exception as e:
        return jsonify({"error": f"AI analysis failed: {e}"}), 500

    # 4. Validate
    validated = validate(result["mappings"], pages)

    # 5. Refine — multi-match fields
    refined_fields = []
    multi = find_multi_matches(result["mappings"], pages)
    if multi:
        updated_mappings = dict(result["mappings"])

        # 5a. Identical values — mechanical narrowing (add intermediate class path)
        narrowed = narrow_by_first_match(result["mappings"], multi, pages)
        if narrowed:
            updated_mappings.update(narrowed)
            refined_fields.extend(narrowed.keys())

        # 5b. Different values — AI refine
        ai_targets = {k: v for k, v in multi.items() if not v.get("all_identical") and k not in narrowed}
        if ai_targets:
            try:
                ai_refined = refine(ai_targets)
                if ai_refined:
                    updated_mappings.update(ai_refined)
                    refined_fields.extend(ai_refined.keys())
            except Exception:
                pass

        if refined_fields:
            validated = validate(updated_mappings, pages)

    # Build response
    site = urlparse(urls[0]).netloc
    elapsed = round(time.time() - t0, 1)

    resp_data = {
        "site": site,
        "mappings": validated,
        "pages_analyzed": len(fetched),
        "pages_failed": len(pages) - len(fetched),
        "tokens_used": result.get("tokens_used", 0),
        "elapsed_seconds": elapsed,
    }
    if refined_fields:
        resp_data["refined_fields"] = refined_fields
    return jsonify(resp_data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8789, threaded=True, debug=False)
