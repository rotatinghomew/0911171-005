"""标注行的规范化、版本管理、分歧检测与证据单元合并。

证据单元 = （章节， 段落， 规范人物）。同一单元的多行标注（多次标注、
多名标注者、同一人物的不同别名）只计一次，不能堆叠为独立证据。
"""


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


def dedupe_key(row: dict) -> tuple:
    return (row["chapter"], row.get("segment"), row["character"])


def _sort_key(key: tuple) -> tuple:
    return (key[0], "" if key[1] is None else str(key[1]), key[2])


def _normalized_appears(row: dict) -> bool:
    appears = row.get("appears")
    if appears is None:
        return row.get("mentions", 0) > 0
    return bool(appears)


def _value_tuple(row: dict) -> tuple:
    return (
        _normalized_appears(row),
        row.get("mentions", 0),
        row.get("narrative_length", 0),
    )


def latest_per_annotator(rows: list[dict]) -> list[dict]:
    """每位标注者在同一证据单元上只保留最高版本；撤回的版本使该记录失效。"""
    latest: dict[tuple, dict] = {}
    for row in rows:
        key = (
            row["chapter"],
            row.get("segment"),
            row["character"],
            row.get("annotator"),
        )
        if key not in latest or row["revision"] > latest[key]["revision"]:
            latest[key] = row
    return [row for row in latest.values() if not row.get("withdrawn", False)]


def find_disagreements(rows: list[dict], adjudications: dict | None = None) -> list[dict]:
    """找出同一证据单元上标注者之间尚未裁决的取值分歧。"""
    adjudications = adjudications or {}
    by_key: dict[tuple, list[dict]] = {}
    for row in latest_per_annotator(rows):
        by_key.setdefault(dedupe_key(row), []).append(row)
    disagreements = []
    for key in sorted(by_key, key=_sort_key):
        if key in adjudications:
            continue
        group = by_key[key]
        if len({_value_tuple(row) for row in group}) > 1:
            chapter, segment, character = key
            disagreements.append({
                "chapter": chapter,
                "segment": segment,
                "character": character,
                "annotations": [dict(row) for row in group],
            })
    return disagreements


def collapse_annotations(rows: list[dict], adjudications: dict | None = None) -> tuple[list[dict], list[dict]]:
    """把多行标注合并为证据单元。

    返回 (units, unresolved)：
    - 已裁决的键采用裁决值；
    - 取值一致的多行（含别名、多次标注、多名标注者）只计一次；
    - 未裁决的分歧不计入统计，放入 unresolved 供查看与裁决。
    """
    adjudications = adjudications or {}
    by_key: dict[tuple, list[dict]] = {}
    for row in latest_per_annotator(rows):
        by_key.setdefault(dedupe_key(row), []).append(row)
    units: list[dict] = []
    unresolved: list[dict] = []
    for key in sorted(by_key, key=_sort_key):
        chapter, segment, character = key
        group = by_key[key]
        sources = [row["id"] for row in group if row.get("id") is not None]
        if key in adjudications:
            res = adjudications[key]
            units.append({
                "chapter": chapter,
                "segment": segment,
                "character": character,
                "appears": res.get("appears"),
                "mentions": res.get("mentions", 0),
                "narrative_length": res.get("narrative_length", 0),
                "adjudicated": True,
                "editor": res.get("editor"),
                "sources": sources,
            })
        elif len({_value_tuple(row) for row in group}) == 1:
            row = group[0]
            units.append({
                "chapter": chapter,
                "segment": segment,
                "character": character,
                "appears": row.get("appears"),
                "mentions": row.get("mentions", 0),
                "narrative_length": row.get("narrative_length", 0),
                "adjudicated": False,
                "editor": None,
                "sources": sources,
            })
        else:
            unresolved.append({
                "chapter": chapter,
                "segment": segment,
                "character": character,
                "annotations": [dict(r) for r in group],
            })
    for unit in units:
        if unit["appears"] is None:
            unit["appears"] = unit["mentions"] > 0
    return units, unresolved
