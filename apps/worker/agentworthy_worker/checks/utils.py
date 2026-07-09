"""Shared HTML parsing helpers for static checks."""

import json
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def extract_text(html: str) -> str:
    soup = make_soup(html)
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def extract_json_ld(html: str) -> list[dict[str, Any]]:
    soup = make_soup(html)
    blocks: list[dict[str, Any]] = []
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                blocks.extend(item for item in data if isinstance(item, dict))
            elif isinstance(data, dict):
                blocks.append(data)
        except json.JSONDecodeError:
            continue
    return blocks


def schema_types(blocks: list[dict[str, Any]]) -> set[str]:
    types: set[str] = set()
    for block in blocks:
        t = block.get("@type")
        if isinstance(t, str):
            types.add(t)
        elif isinstance(t, list):
            types.update(x for x in t if isinstance(x, str))
        graph = block.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict) and isinstance(item.get("@type"), str):
                    types.add(item["@type"])
    return types


def find_canonicals(html: str, page_url: str) -> list[str]:
    soup = make_soup(html)
    urls: list[str] = []
    for link in soup.find_all("link", rel=True):
        rel = link.get("rel")
        if rel and "canonical" in [r.lower() for r in (rel if isinstance(rel, list) else [rel])]:
            href = link.get("href")
            if href:
                urls.append(urljoin(page_url, href))
    return urls


def extract_phones(text: str) -> set[str]:
    pattern = r"\+?[\d\s().-]{10,}"
    return {re.sub(r"\s+", "", m) for m in re.findall(pattern, text) if len(re.sub(r"\D", "", m)) >= 10}


def extract_emails(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))


PHONE_RE = re.compile(r"\+?[\d\s().-]{10,}")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def same_origin(base: str, url: str) -> bool:
    b, u = urlparse(base), urlparse(url)
    return b.netloc == u.netloc and b.scheme == u.scheme


def is_interactive(tag: Tag) -> bool:
    return tag.name in ("button", "a", "input", "select", "textarea")
