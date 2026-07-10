"""SSRF guard shared by crawler and simulator."""

import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "metadata.google.internal"}
BLOCKED_IP = ipaddress.ip_address("169.254.169.254")


def validate_scan_url(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URL scheme not allowed: {parsed.scheme}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("URL has no hostname")
    if host in BLOCKED_HOSTS:
        raise ValueError(f"Blocked host: {host}")
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as e:
        raise ValueError(f"DNS resolution failed for {host}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip == BLOCKED_IP:
            raise ValueError("Blocked metadata IP")
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError(f"Private/reserved IP blocked: {ip}")
    return f"{parsed.scheme}://{host}{parsed.path or ''}"
