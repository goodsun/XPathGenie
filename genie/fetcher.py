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


def _check_ssrf(url: str):
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
    for _, _, _, _, addr in resolved:
        ip = ipaddress.ip_address(addr[0])
        for net in BLOCKED_NETWORKS:
            if ip in net:
                raise ValueError(f"Blocked private IP: {ip}")


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
    # Try to decode
    encoding = resp.encoding or "utf-8"
    try:
        return content.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return content.decode("utf-8", errors="replace")


def fetch_all(urls: list) -> list:
    """Fetch all URLs. Returns list of {url, html, error}."""
    results = []
    for url in urls:
        try:
            html = fetch(url)
            results.append({"url": url, "html": html, "error": None})
        except Exception as e:
            results.append({"url": url, "html": None, "error": str(e)})
    return results
