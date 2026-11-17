def select_scope(rows: list[dict], chapter_ids: set[str]) -> list[dict]:
    return [row for row in rows if row["chapter"] in chapter_ids]
