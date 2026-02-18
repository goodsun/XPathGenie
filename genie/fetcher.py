"""HTML fetcher with SSRF protection."""

import ipaddress
import socket
from urllib.parse import urlparse
import requests

MAX_SIZE = 10 * 1024 * 1024  # 10MB
TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _check_ssrf(url: str) -> list:
    """Check SSRF and return list of resolved safe IPs.

    Note on DNS rebinding: We resolve and validate IPs here, then rely on
    OS-level DNS cache (typically 60s+) so the subsequent requests.get()
    connects to the same validated IP. A full fix (forcing IP connection)
    would break TLS hostname verification without significant complexity.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Blocked scheme: {parsed.scheme}")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("No hostname")
    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve: {hostname}")
    safe_ips = []
    for _, _, _, _, addr in resolved:
        ip = ipaddress.ip_address(addr[0])
        for net in BLOCKED_NETWORKS:
            if ip in net:
                raise ValueError(f"Blocked private IP: {ip}")
        safe_ips.append(addr[0])
    return safe_ips


def _detect_encoding(content: bytes, resp_encoding: str = None) -> str:
    """Detect encoding from HTTP header, meta tag, or chardet."""
    # 1. HTTP Content-Type header
    if resp_encoding and resp_encoding.lower() not in ("utf-8", "iso-8859-1", "ascii"):
        return resp_encoding

    # 2. HTML meta charset
    import re
    head = content[:4096]
    # <meta charset="...">
    m = re.search(rb'<meta[^>]+charset=["\']?([a-zA-Z0-9_-]+)', head, re.IGNORECASE)
    if m:
        return m.group(1).decode("ascii", errors="ignore")
    # <meta http-equiv="Content-Type" content="text/html; charset=...">
    m = re.search(rb'content=["\'][^"\']*charset=([a-zA-Z0-9_-]+)', head, re.IGNORECASE)
    if m:
        return m.group(1).decode("ascii", errors="ignore")

    # 3. Default
    return resp_encoding or "utf-8"


def _clean_html(html: str) -> str:
    """Remove XML declaration and DOCTYPE that break lxml HTML parser."""
    import re
    html = re.sub(r'<\?xml[^>]*\?>', '', html, count=1)
    html = re.sub(r'<!DOCTYPE[^>]*>', '', html, count=1, flags=re.IGNORECASE)
    return html


def fetch(url: str) -> str:
    """Fetch HTML from URL. Returns HTML string."""
    _check_ssrf(url)
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        stream=True,
    )
    resp.raise_for_status()
    content = resp.content[:MAX_SIZE]
    # Detect encoding (supports Shift-JIS, EUC-JP, etc.)
    encoding = _detect_encoding(content, resp.encoding)
    try:
        html = content.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        # Fallback: try common Japanese encodings
        html = None
        for enc in ("utf-8", "shift_jis", "euc-jp", "cp932"):
            try:
                html = content.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        if html is None:
            html = content.decode("utf-8", errors="replace")
    return _clean_html(html)


def fetch_all(urls: list) -> list:
    """Fetch all URLs in parallel. Returns list of {url, html, error}."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_one(url):
        try:
            html = fetch(url)
            return {"url": url, "html": html, "error": None}
        except Exception as e:
            return {"url": url, "html": None, "error": str(e)}

    results = [None] * len(urls)
    with ThreadPoolExecutor(max_workers=min(len(urls), 5)) as executor:
        future_to_idx = {executor.submit(_fetch_one, url): i for i, url in enumerate(urls)}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()
    return results
