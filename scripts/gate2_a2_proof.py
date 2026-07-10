#!/usr/bin/env python3
"""A2 proof: reset DB from zero, migrate, auth sync + site creation."""

import json
import os
import subprocess
import sys

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.environ.get("API_URL", "http://localhost:8000")
DB = os.environ.get("DATABASE_URL", "postgresql://agentworthy@localhost:5432/agentworthy")


def run(cmd: list[str], cwd: str | None = None) -> str:
    return subprocess.check_output(cmd, text=True, cwd=cwd or ROOT)


def main() -> None:
    print("=== A2: Drop and recreate schema ===")
    drop_sql = """
    DROP SCHEMA public CASCADE;
    CREATE SCHEMA public;
    GRANT ALL ON SCHEMA public TO agentworthy;
    GRANT ALL ON SCHEMA public TO public;
    """
    run(["psql", DB, "-c", drop_sql.replace("\n", " ")])
    mig = run(["python3", "-m", "alembic", "upgrade", "head"], cwd=os.path.join(ROOT, "apps", "api"))
    print(mig)

    print("\n=== A2: Auth sync + site creation ===")
    with httpx.Client(base_url=API, timeout=30) as client:
        sync = client.post("/auth/sync", json={"email": "a2-proof@agentworthy.example", "name": "A2 Proof"})
        sync.raise_for_status()
        token = sync.json()["access_token"]
        print("auth/sync:", json.dumps(sync.json(), indent=2, default=str))

        site = client.post(
            "/sites",
            json={"root_url": "http://localhost:8765", "display_name": "A2 Proof Site"},
            headers={"Authorization": f"Bearer {token}"},
        )
        site.raise_for_status()
        print("sites/create:", json.dumps(site.json(), indent=2, default=str))


if __name__ == "__main__":
    main()
