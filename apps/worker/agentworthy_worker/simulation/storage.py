"""Local filesystem storage for simulation screenshots."""

import os
from pathlib import Path


class LocalStorage:
    def __init__(self, base_path: str | None = None) -> None:
        self.base = Path(base_path or os.environ.get("SCREENSHOT_PATH", "/data/screenshots"))

    def path_for(self, scan_id: str, sim_id: str, step: int) -> Path:
        rel = Path(scan_id) / sim_id / f"{step}.png"
        full = self.base / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        return full

    def save_bytes(self, scan_id: str, sim_id: str, step: int, data: bytes) -> str:
        path = self.path_for(scan_id, sim_id, step)
        path.write_bytes(data)
        return str(path)
