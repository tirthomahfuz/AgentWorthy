"""Site ownership verification via meta tag or DNS TXT."""

import re
import secrets
from urllib.parse import urlparse

import dns.resolver
import httpx


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def meta_tag_html(token: str) -> str:
    return f'<meta name="agentworthy-verification" content="{token}" />'


def dns_txt_record(token: str) -> str:
    return f"agentworthy-verification={token}"


def check_meta_tag(root_url: str, token: str, client: httpx.Client | None = None) -> bool:
    parsed = urlparse(root_url if "://" in root_url else f"https://{root_url}")
    url = f"{parsed.scheme}://{parsed.netloc}/"
    own_client = client is None
    http = client or httpx.Client(follow_redirects=True, timeout=15.0)
    try:
        response = http.get(url)
        if response.status_code >= 400:
            return False
        html = response.text
        pattern = rf'<meta[^>]+name=["\']agentworthy-verification["\'][^>]+content=["\']{re.escape(token)}["\']'
        pattern2 = rf'<meta[^>]+content=["\']{re.escape(token)}["\'][^>]+name=["\']agentworthy-verification["\']'
        return bool(re.search(pattern, html, re.I) or re.search(pattern2, html, re.I))
    except httpx.HTTPError:
        return False
    finally:
        if own_client:
            http.close()


def check_dns_txt(root_url: str, token: str) -> bool:
    parsed = urlparse(root_url if "://" in root_url else f"https://{root_url}")
    host = parsed.netloc
    expected = dns_txt_record(token)
    try:
        answers = dns.resolver.resolve(host, "TXT")
        for rdata in answers:
            txt = rdata.to_text().strip('"')
            if txt == expected or expected in txt:
                return True
        return False
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
        return False


def verify_ownership(root_url: str, token: str) -> tuple[bool, str, dict[str, bool]]:
    with httpx.Client(follow_redirects=True, timeout=15.0) as client:
        meta_ok = check_meta_tag(root_url, token, client)
    txt_ok = check_dns_txt(root_url, token)
    if meta_ok:
        return True, "verified via meta tag", {"meta_tag": True, "dns_txt": txt_ok}
    if txt_ok:
        return True, "verified via DNS TXT record", {"meta_tag": False, "dns_txt": True}
    return False, "verification token not found in meta tag or DNS TXT", {"meta_tag": False, "dns_txt": False}
