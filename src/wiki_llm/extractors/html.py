from pathlib import Path

import markdownify


def extract(filePath: Path) -> str:
    """Convert HTML to markdown using markdownify"""

    html = filePath.read_text(encoding="utf-8")
    return markdownify.markdownify(html, heading_style="ATX")
