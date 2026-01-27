from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from gpvb.models import PageResult


class Storage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pages (
                    url TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
                """
            )

    def save_pages(self, pages: Iterable[PageResult]) -> None:
        with sqlite3.connect(self.path) as conn:
            for page in pages:
                conn.execute(
                    "INSERT OR REPLACE INTO pages (url, data) VALUES (?, ?)",
                    (page.url, json.dumps(page.model_dump())),
                )

    def load_page(self, url: str) -> Optional[PageResult]:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT data FROM pages WHERE url = ?", (url,)).fetchone()
            if not row:
                return None
            return PageResult.model_validate_json(row[0])
