def canonicalize(rows: list[dict], aliases: dict[str, str]) -> list[dict]:
    result = []
    for row in rows:
        item = dict(row)
        item["character"] = aliases.get(row["character"], row["character"])
        result.append(item)
    return result


def current_annotations(rows: list[dict]) -> list[dict]:
    latest: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["chapter"], row["character"])
        if key not in latest or row["revision"] > latest[key]["revision"]:
            latest[key] = row
    return [row for row in latest.values() if not row.get("withdrawn", False)]
