"""Redis client and rate limiting."""

import hashlib
from datetime import UTC, datetime

import redis

from agentworthy.config import get_settings


def get_redis() -> redis.Redis:  # type: ignore[type-arg]
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()


def check_rate_limit(ip_hash: str) -> tuple[bool, int]:
    """Return (allowed, remaining_scans_today)."""
    settings = get_settings()
    r = get_redis()
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    key = f"rate_limit:public_scan:{ip_hash}:{today}"
    current = r.get(key)
    count = int(current) if current else 0
    remaining = max(0, settings.free_scans_per_day - count)
    return count < settings.free_scans_per_day, remaining


def increment_rate_limit(ip_hash: str) -> None:
    settings = get_settings()
    r = get_redis()
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    key = f"rate_limit:public_scan:{ip_hash}:{today}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, 86400)
    pipe.execute()


def enqueue_scan(scan_id: str) -> None:
    """Enqueue a public scan job to RQ."""
    from rq import Queue

    settings = get_settings()
    r = get_redis()
    queue = Queue("scans", connection=r)
    queue.enqueue("agentworthy_worker.jobs.run_static_scan", scan_id, job_timeout="10m")


def enqueue_site_scan(scan_id: str, root_url: str, max_pages: int) -> None:
    from rq import Queue

    r = get_redis()
    queue = Queue("scans", connection=r)
    queue.enqueue(
        "agentworthy_worker.jobs.run_site_scan",
        scan_id,
        root_url,
        max_pages,
        job_timeout="15m",
    )
