from __future__ import annotations

from pathlib import Path
import re
import sqlite3

from wiki_llm.exceptions import WikiIndexError
from wiki_llm.indexing import SearchResult
from wiki_llm.wiki.reader import WikiPage


def _sanitize(query: str) -> str:
    """Strip FTS5 operator characters so plain-text queries never raise."""
    return re.sub(r'[-^*"()]', " ", query).strip()


_SCHEMA = """
    CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(
        path UNINDEXED,
        title,
        body,
        tags,
        tokenize = 'unicode61 remove_diacritics 1'
    )
"""


class BM25Index:
    def __init__(self, db_path: Path) -> None:
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.__conn = sqlite3.connect(str(db_path))
            self.__conn.execute(_SCHEMA)
            self.__conn.commit()
        except sqlite3.Error as err:
            raise WikiIndexError(str(err)) from err

    def upsert(self, page: WikiPage) -> None:
        """Insert or replace a page in the index."""
        try:
            path_str = str(page.path)
            self.__conn.execute("DELETE FROM pages WHERE path = ?", (path_str,))
            self.__conn.execute(
                "INSERT INTO pages (path, title, body, tags) VALUES (?, ?, ?, ?)",
                (path_str, page.title, page.body, " ".join(page.tags)),
            )
            self.__conn.commit()
        except sqlite3.Error as exc:
            raise WikiIndexError(str(exc)) from exc

    def delete(self, page_path: Path) -> None:
        """Remove a page from the index."""
        try:
            self.__conn.execute("DELETE FROM pages WHERE path = ?", (str(page_path),))
            self.__conn.commit()
        except sqlite3.Error as exc:
            raise WikiIndexError(str(exc)) from exc

    # --- read ---

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Full-text BM25 search. Returns results ranked best-first."""
        clean = _sanitize(query)
        if not clean:
            return []
        try:
            cursor = self.__conn.execute(
                """
                SELECT path, title, bm25(pages) AS score
                FROM pages
                WHERE pages MATCH ?
                ORDER BY score        -- FTS5 bm25() is negative; lower = better
                LIMIT ?
                """,
                (clean, top_k),
            )
            return [
                SearchResult(path=Path(row[0]), title=row[1], score=-row[2])
                for row in cursor.fetchall()
            ]
        except sqlite3.Error as exc:
            raise WikiIndexError(str(exc)) from exc

    def count(self) -> int:
        """Number of pages currently indexed."""
        row = self.__conn.execute("SELECT count(*) FROM pages").fetchone()
        return row[0]

    def close(self) -> None:
        self.__conn.close()

    def __enter__(self) -> BM25Index:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
