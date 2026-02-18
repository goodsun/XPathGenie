"""XPathGenie — Flask API + static file server."""

from flask import Flask, request, jsonify, send_from_directory
from urllib.parse import urlparse
import os
import time
import threading
import ipaddress

from genie.fetcher import fetch_all
from genie.compressor import compress
from genie.analyzer import analyze, refine
from genie.validator import validate, find_multi_matches, narrow_by_first_match

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Simple rate limiting for API endpoints (thread-safe)
_rate_limit = {}
_rate_lock = threading.Lock()
_rate_cleanup_counter = 0
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 30  # requests per window
_RATE_CLEANUP_INTERVAL = 100  # cleanup every N calls
_RATE_CLEANUP_MAX_AGE = 120  # seconds

def _check_rate_limit(key: str) -> bool:
    global _rate_cleanup_counter
    now = time.time()
    with _rate_lock:
        # Periodic cleanup of stale entries
        _rate_cleanup_counter += 1
        if _rate_cleanup_counter >= _RATE_CLEANUP_INTERVAL:
            _rate_cleanup_counter = 0
            expired = [k for k, ts_list in _rate_limit.items()
                       if not ts_list or now - ts_list[-1] > _RATE_CLEANUP_MAX_AGE]
            for k in expired:
                del _rate_limit[k]

        if key not in _rate_limit:
            _rate_limit[key] = []
        _rate_limit[key] = [t for t in _rate_limit[key] if now - t < RATE_LIMIT_WINDOW]
        if len(_rate_limit[key]) >= RATE_LIMIT_MAX:
            return False
        _rate_limit[key].append(now)
    return True

ALLOWED_ORIGINS = {"corp.bon-soleil.com", "bizendao.github.io", "localhost", "127.0.0.1"}

def _check_origin() -> bool:
    """Check Referer/Origin to prevent open proxy abuse."""
    referer = request.headers.get("Referer", "")
    origin = request.headers.get("Origin", "")
    for header in (referer, origin):
        if header:
            try:
                host = urlparse(header).hostname or ""
                if any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_ORIGINS):
                    return True
            except Exception:
                pass
    # Allow requests from reverse proxy (Apache on same host)
    if request.remote_addr in ("127.0.0.1", "::1"):
        return True
    # Block requests with empty Origin/Referer (prevent open proxy abuse)
    return False


@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/api/fetch")
def api_fetch():
    """Fetch HTML for Aladdin page (server-side to avoid CORS)."""
    if not _check_origin():
        return jsonify({"error": "Forbidden"}), 403
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
    if not _check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded"}), 429
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "url required"}), 400
    # SSRF protection: block internal/private IPs
    try:
        host = urlparse(url).hostname or ""
        addr = ipaddress.ip_address(host) if host.replace(".", "").isdigit() or ":" in host else None
        if addr and (addr.is_private or addr.is_loopback or addr.is_reserved):
            return jsonify({"error": "Internal addresses not allowed"}), 403
        if host.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return jsonify({"error": "Internal addresses not allowed"}), 403
    except (ValueError, TypeError):
        pass
    try:
        pages = fetch_all([url])
        if pages and pages[0].get("html"):
            return jsonify({"html": pages[0]["html"], "url": url})
        return jsonify({"error": pages[0].get("error", "fetch failed")}), 400
    except Exception as e:
        app.logger.exception("Fetch error")
        return jsonify({"error": "Failed to fetch URL"}), 500


@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://unpkg.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


def _get_user_api_key(data):
    """Extract API key: Authorization header takes priority, POST body as fallback."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        key = auth[7:].strip()
        if key:
            return key
    return (data.get("api_key") or "").strip()


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    if not _check_origin():
        return jsonify({"error": "Forbidden"}), 403
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
    if not _check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded"}), 429
    data = request.get_json()
    if not data or "urls" not in data:
        return jsonify({"error": "urls required"}), 400

    # BYOK: get API key from Authorization header or POST body
    api_key = _get_user_api_key(data)
    allow_server_key = os.environ.get("XPATHGENIE_ALLOW_SERVER_KEY") == "1"
    if not api_key and not allow_server_key:
        return jsonify({"error": "API key required. Please enter your Gemini API key."}), 401

    urls = [u.strip() for u in data["urls"] if u.strip()]
    if not urls:
        return jsonify({"error": "No valid URLs"}), 400
    if len(urls) > 10:
        return jsonify({"error": "Max 10 URLs"}), 400

    t0 = time.time()
    diagnostics = {}

    # 1. Fetch
    pages = fetch_all(urls)
    fetched = [p for p in pages if p["html"]]
    if not fetched:
        fetch_errors = [p.get("error", "unknown") for p in pages]
        reason = "fetch_failed"
        suggestion = "Check if the site requires JavaScript rendering (SPA) or blocks automated access."
        if any("403" in str(e) for e in fetch_errors):
            reason = "access_denied"
            suggestion = "Site returned 403 Forbidden. May require authentication or block bots."
        elif any("timeout" in str(e).lower() for e in fetch_errors):
            reason = "timeout"
            suggestion = "Request timed out. Site may be slow or blocking requests."
        return jsonify({
            "status": "error",
            "reason": reason,
            "message": "Failed to fetch all URLs",
            "details": fetch_errors,
            "suggestion": suggestion,
        }), 400

    # 1b. Encoding diagnostics
    for p in fetched:
        html = p["html"]
        # Check for mojibake indicators (garbled Shift-JIS decoded as UTF-8)
        if html and ('\ufffd' in html[:2000] or any(ord(c) > 0xFFFD for c in html[:2000])):
            diagnostics["encoding_warning"] = "Possible encoding issues detected in fetched HTML"

    # 2. Compress
    compressed = []
    for p in fetched:
        c = compress(p["html"])
        compressed.append(c)

    # 2b. Check compressed size
    total_compressed = sum(len(c) for c in compressed)
    diagnostics["compressed_size_bytes"] = total_compressed
    if total_compressed == 0:
        return jsonify({
            "status": "error",
            "reason": "compression_empty",
            "message": "HTML compression produced empty output — the page structure could not be parsed. "
                       "This may indicate a JavaScript-rendered SPA or an unsupported HTML structure.",
            "suggestion": "Try a page with server-rendered HTML content.",
            "diagnostics": diagnostics,
        }), 422
    if total_compressed < 100:
        diagnostics["compression_warning"] = "Compressed HTML is very small — page may lack structured content (SPA?)"

    # 3. Analyze with Gemini
    wantlist = data.get("wantlist")  # optional: {"field": "", ...}
    try:
        result = analyze(compressed, wantlist=wantlist, api_key=api_key or None)
    except Exception as e:
        app.logger.exception("Analyze error")
        return jsonify({
            "status": "error",
            "reason": "analysis_failed",
            "message": "AI analysis failed. Please check your API key and try again.",
            "suggestion": "The AI could not extract field mappings. The page structure may be too complex or non-standard.",
            "diagnostics": diagnostics,
        }), 500

    # 3b. Check if zero mappings returned
    if not result.get("mappings"):
        return jsonify({
            "status": "error",
            "reason": "no_fields_detected",
            "message": "AI analysis completed but returned 0 fields",
            "suggestion": "The page may use JavaScript rendering (SPA), have non-standard HTML structure, or encoding issues.",
            "diagnostics": diagnostics,
        }), 200

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
                ai_refined = refine(ai_targets, api_key=api_key or None)
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
        "status": "ok",
        "site": site,
        "mappings": validated,
        "pages_analyzed": len(fetched),
        "pages_failed": len(pages) - len(fetched),
        "tokens_used": result.get("tokens_used", 0),
        "elapsed_seconds": elapsed,
    }
    if refined_fields:
        resp_data["refined_fields"] = refined_fields
    if diagnostics:
        resp_data["diagnostics"] = diagnostics
    return jsonify(resp_data)


@app.route("/docs/<path:filename>")
def serve_docs(filename):
    """Serve files from the docs directory."""
    docs_dir = os.path.join(os.path.dirname(__file__), "docs")
    return send_from_directory(docs_dir, filename)


@app.route("/whitepaper.html")
def serve_whitepaper():
    """Serve the whitepaper HTML file."""
    app_dir = os.path.dirname(__file__)
    return send_from_directory(app_dir, "whitepaper.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8789, threaded=True, debug=False)
