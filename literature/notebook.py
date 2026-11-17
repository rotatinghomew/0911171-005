from copy import deepcopy

from .analysis import prominence


class ResearchNotebook:
    def __init__(self, chapter_frame: list[dict]) -> None:
        self.frame = {chapter["chapter"]: deepcopy(chapter) for chapter in chapter_frame}
        if len(self.frame) != len(chapter_frame):
            raise ValueError("章节抽样框含重复编号")
        self.notes: dict[str, dict] = {}

    def describe(self, note_id: str, annotations: list[dict], aliases: dict[str, str], chapters: set[str], method: str) -> dict:
        if not chapters.issubset(self.frame):
            raise ValueError("分析范围超出登记的章节框")
        if method not in {"census", "convenience"}:
            raise ValueError("未登记的样本选取方式")
        if method == "census" and chapters != set(self.frame):
            raise ValueError("全量分析必须纳入整个章节框")
        result = {
            "method": method,
            "chapters": sorted(chapters),
            "frame_size": len(self.frame),
            "aliases": deepcopy(aliases),
            "annotations": deepcopy(annotations),
            "statistics": prominence(annotations, aliases, chapters),
        }
        if note_id in self.notes and self.notes[note_id] != result:
            raise ValueError("研究笔记编号不能复用为不同分析")
        self.notes[note_id] = result
        return deepcopy(result)

    def evidence(self, note_id: str, character: str) -> list[dict]:
        note = self.notes[note_id]
        return deepcopy([
            row for row in note["annotations"]
            if row["chapter"] in note["chapters"]
            and note["aliases"].get(row["character"], row["character"]) == character
        ])
