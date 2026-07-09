"""Build crawl context and render homepage."""

import logging
import time
from urllib.parse import urlparse

import httpx

from agentworthy_worker.checks.context import CrawlContext
from agentworthy_worker.checks.utils import extract_text, make_soup
from agentworthy_worker.crawler import CRAWLER_USER_AGENT, crawl_site
from agentworthy_worker.llm.client import classify_site_type

logger = logging.getLogger(__name__)


def fetch_homepage_metrics(client: httpx.Client, root_url: str) -> tuple[float, int]:
    start = time.perf_counter()
    resp = client.get(root_url, timeout=15.0)
    ttfb_ms = (time.perf_counter() - start) * 1000
    return ttfb_ms, len(resp.content)


def render_homepage(root_url: str) -> tuple[str | None, bool]:
    """Return (rendered_html, render_blocked)."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=CRAWLER_USER_AGENT)
            response = page.goto(root_url, wait_until="networkidle", timeout=30000)
            if response and response.status in (403, 429, 503):
                browser.close()
                return None, True
            html = page.content()
            browser.close()
            return html, False
    except Exception as e:
        err = str(e).lower()
        blocked = any(k in err for k in ("blocked", "403", "captcha", "denied", "timeout"))
        logger.warning("Playwright render failed", extra={"error": str(e)})
        return None, blocked


def build_crawl_context(
    client: httpx.Client,
    root_url: str,
    max_pages: int = 25,
    scan_id: str | None = None,
) -> CrawlContext:
    parsed = urlparse(root_url)
    root_url = f"{parsed.scheme}://{parsed.netloc}"

    robots_content: str | None = None
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        r = client.get(robots_url, timeout=10.0)
        if r.status_code == 200:
            robots_content = r.text
    except httpx.HTTPError:
        pass

    ttfb_ms, weight = fetch_homepage_metrics(client, root_url)
    pages = crawl_site(root_url, max_pages=max_pages)
    rendered, render_blocked = render_homepage(root_url)

    site_type: str | None = None
    html = pages.get(root_url.rstrip("/")) or pages.get(root_url) or next(iter(pages.values()), None)
    if html:
        soup = make_soup(html)
        title = soup.find("title")
        title_text = title.get_text(strip=True) if title else ""
        site_type = classify_site_type(title_text, extract_text(html)[:3000], scan_id=scan_id)

    return CrawlContext(
        root_url=root_url,
        pages=pages,
        client=client,
        robots_content=robots_content,
        rendered_homepage_html=rendered,
        render_blocked=render_blocked,
        site_type=site_type,
        homepage_ttfb_ms=ttfb_ms,
        homepage_weight_bytes=weight,
        scan_id=scan_id,
    )
