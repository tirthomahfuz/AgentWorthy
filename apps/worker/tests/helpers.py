"""Test helpers for static checks."""

import httpx

from agentworthy_worker.checks.context import CrawlContext


class MockTransport(httpx.BaseTransport):
    def __init__(self, responses: dict[str, tuple[int, str]], default_status: int = 404) -> None:
        self.responses = responses
        self.default_status = default_status

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for pattern, (status, body) in self.responses.items():
            if pattern in url:
                headers = {"content-type": "text/html"} if "<html" in body.lower() else {}
                if "sitemap" in url or "<?xml" in body:
                    headers = {"content-type": "application/xml"}
                return httpx.Response(status, text=body, headers=headers)
        return httpx.Response(self.default_status, text="Not Found")


def make_ctx(
    root_url: str = "https://example.com",
    responses: dict[str, tuple[int, str]] | None = None,
    pages: dict[str, str] | None = None,
    **kwargs: object,
) -> CrawlContext:
    transport = MockTransport(responses or {})
    client = httpx.Client(transport=transport, base_url=root_url)
    default_pages = pages or {}
    if not default_pages and responses:
        for pattern, (_, body) in responses.items():
            if "<html" in body.lower():
                default_pages[root_url] = body
    return CrawlContext(
        root_url=root_url,
        pages=default_pages,
        client=client,
        **kwargs,  # type: ignore[arg-type]
    )
