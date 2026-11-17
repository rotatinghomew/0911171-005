from .annotations import canonicalize, current_annotations
from .scope import select_scope


def prominence(rows: list[dict], aliases: dict[str, str], chapter_ids: set[str]) -> dict:
    normalized = canonicalize(rows, aliases)
    selected = select_scope(current_annotations(normalized), chapter_ids)
    counts: dict[str, int] = {}
    for row in selected:
        counts[row["character"]] = counts.get(row["character"], 0) + int(row["mentions"])
    return {"chapter_count": len(chapter_ids), "annotation_count": len(selected), "mentions": dict(sorted(counts.items()))}
