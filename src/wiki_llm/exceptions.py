class WikiError(Exception):
    """Base class for all wiki-llm errors."""


class PageNotFound(WikiError):
    """Raised when a wiki page path does not exist on disk."""

    def __init__(self, path: object) -> None:
        super().__init__(f"Wiki page not found: {path}")
        self.path = path


class PageParseError(WikiError):
    """Raised when a page file cannot be parsed (bad frontmatter or schema)."""

    def __init__(self, path: object, reason: str) -> None:
        super().__init__(f"Failed to parse wiki page {path}: {reason}")
        self.path = path
        self.reason = reason


class UnsupportedFileType(WikiError):
    """Raised when no extractor exists for the given file extension."""

    def __init__(self, path: object, ext: str) -> None:
        super().__init__(f"No extractor for '{ext}' ({path})")
        self.path = path
        self.ext = ext


class WikiIndexError(WikiError):
    """Raised when an index operation (BM25 or vector) fails."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Index error: {reason}")
        self.reason = reason


class LLMError(WikiError):
    """Raised when an LLM API call fails."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"LLM error: {reason}")
        self.reason = reason
