"""Breadth-first site crawler respecting robots.txt."""

import logging
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from urllib import robotparser

logger = logging.getLogger(__name__)

CRAWLER_USER_AGENT = "AgentworthyBot/1.0 (+https://agentworthy.com)"


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def is_same_origin(base: str, url: str) -> bool:
    base_parsed = urlparse(base)
    url_parsed = urlparse(url)
    return base_parsed.netloc == url_parsed.netloc and base_parsed.scheme == url_parsed.scheme


def extract_links(html: str, base_url: str) -> list[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        if is_same_origin(base_url, absolute):
            links.append(normalize_url(absolute))
    return links


def fetch_robots(root_url: str, client: httpx.Client) -> robotparser.RobotFileParser | None:
    parsed = urlparse(root_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = client.get(robots_url, timeout=10.0)
        if response.status_code == 200:
            rp = robotparser.RobotFileParser()
            rp.parse(response.text.splitlines())
            return rp
    except httpx.HTTPError:
        pass
    return None


def crawl_site(root_url: str, max_pages: int = 25) -> dict[str, str]:
    """BFS crawl returning {url: html} for up to max_pages."""
    parsed_root = urlparse(root_url)
    root_url = f"{parsed_root.scheme}://{parsed_root.netloc}"

    pages: dict[str, str] = {}
    visited: set[str] = set()
    queue: deque[str] = deque([normalize_url(root_url)])

    headers = {"User-Agent": CRAWLER_USER_AGENT}

    with httpx.Client(headers=headers, follow_redirects=True, timeout=15.0) as client:
        protego = fetch_robots(root_url, client)

        while queue and len(pages) < max_pages:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            if protego and not protego.can_fetch(CRAWLER_USER_AGENT, url):
                logger.info("Blocked by robots.txt", extra={"url": url})
                continue

            try:
                response = client.get(url)
                if response.status_code != 200:
                    continue
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    continue
                pages[url] = response.text
                for link in extract_links(response.text, url):
                    if link not in visited:
                        queue.append(link)
            except httpx.HTTPError as e:
                logger.warning("Crawl error", extra={"url": url, "error": str(e)})

    return pages
