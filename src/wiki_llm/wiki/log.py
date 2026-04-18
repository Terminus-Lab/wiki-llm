from __future__ import annotations

import datetime
from pathlib import Path


def append_log(
    log_md: Path,
    source: Path,
    created: list[Path],
    updated: list[Path],
) -> None:
    """Append one ingest entry to log.md"""
    ts = datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [f"## {ts}\n"]
    lines.append(f"- **Source:** {source}")

    if created:
        names = ", ".join(p.name for p in created)
        lines.append(f"- **Created:** {names}")

    if updated:
        names = ", ".join(p.name for p in updated)
        lines.append(f"- **Updated:** {names}")

    lines.append("\n---\n")
    entry = "\n".join(lines)

    log_md.parent.mkdir(parents=True, exist_ok=True)
    with log_md.open("a", encoding="utf-8") as f:
        f.write(entry)
