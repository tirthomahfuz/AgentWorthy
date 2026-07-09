"""RQ worker entry point."""

import logging
import os
import sys

from redis import Redis
from rq import Queue, Worker

# Ensure API package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api"))

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}',
)

logger = logging.getLogger(__name__)


def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    conn = Redis.from_url(redis_url)
    queue = Queue("scans", connection=conn)
    worker = Worker([queue], connection=conn)
    logger.info("Starting RQ worker on queue 'scans'")
    worker.work()


if __name__ == "__main__":
    main()
