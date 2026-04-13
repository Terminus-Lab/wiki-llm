class WikiError(Exception):
    """Base Error for all wiki-llm exceptions"""


class PageNotFound(WikiError):
    """Rase when a wiki page does not exist on the disk"""

    def __init__(self, path: object):
        super().__init__(f"Wiki page not found on: ${path}")
        self.path = path


class PageParseError(WikiError):
    """Raise when a page file cannot be parsed. Bad schema"""

    def __init__(self, path: object, reason: str):
        super().__init__(f"Wiki page: {path}, can't be parse. Reason: {reason}")
        self.path = path
        self.reason = reason


class UnsupportedFileType(WikiError):
    """Raised when no extractor exists for the given file extension."""

    def __init__(self, path: object, ext: str):
        super().__init__(f"No extractors for '{ext}', path: {path}")
        self.path = path
        self.ext = ext


class IndexError(WikiError):
    """Raised when a BM25 index operation fails."""

    def __init__(self, reason: str):
        super().__init__(f"Indexing error. Reason: {reason}")
        self.reason = reason
