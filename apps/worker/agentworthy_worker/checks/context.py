"""Crawl context passed to every static check."""

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class CrawlContext:
    root_url: str
    pages: dict[str, str]
    client: httpx.Client
    robots_content: str | None = None
    sitemap_urls: list[str] = field(default_factory=list)
    rendered_homepage_html: str | None = None
    render_blocked: bool = False
    site_type: str | None = None
    homepage_ttfb_ms: float | None = None
    homepage_weight_bytes: int | None = None
    scan_id: str | None = None

    @property
    def homepage_html(self) -> str | None:
        normalized = self.root_url.rstrip("/")
        if normalized in self.pages:
            return self.pages[normalized]
        if self.root_url in self.pages:
            return self.pages[self.root_url]
        return next(iter(self.pages.values()), None)

    @property
    def homepage_url(self) -> str:
        return self.root_url
