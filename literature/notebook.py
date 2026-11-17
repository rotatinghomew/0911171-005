from copy import deepcopy

from .analysis import birth_order_comparison, prominence
from .annotations import canonicalize, collapse_annotations, find_disagreements, latest_per_annotator
from .kinship import KinshipRegistry
from .sampling import build_plan


class ResearchNotebook:
    def __init__(self, chapter_frame: list[dict]) -> None:
        self.frame = {chapter["chapter"]: deepcopy(chapter) for chapter in chapter_frame}
        if len(self.frame) != len(chapter_frame):
            raise ValueError("章节抽样框含重复编号")
        self.chapter_work = {c: rec.get("work") for c, rec in self.frame.items()}
        self.notes: dict[str, dict] = {}
        self.aliases: dict[str, str] = {}
        self.registry = KinshipRegistry()
        self.annotation_store: list[dict] = []
        self.adjudications: dict[tuple, dict] = {}
        self.plans: dict[str, dict] = {}
        self._seq = 0
        self._excerpt_seq = 0

    # ---- 既有接口：频数描述与证据回看 ----

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
        """笔记发布时保存的原始标注行；裁决与修订不回写已发布笔记。"""
        note = self.notes[note_id]
        return deepcopy([
            row for row in note["annotations"]
            if row["chapter"] in note["chapters"]
            and note["aliases"].get(row["character"], row["character"]) == character
        ])

    def get_note(self, note_id: str) -> dict:
        return deepcopy(self.notes[note_id])

    # ---- 登记：别名、亲属组、标注 ----

    def register_aliases(self, aliases: dict[str, str]) -> None:
        self.aliases.update(aliases)

    def register_kinship_group(self, group_id: str, members: list[dict], work: str | None = None, label: str | None = None) -> dict:
        return self.registry.register(group_id, members, work=work, label=label)

    def register_annotations(self, rows: list[dict]) -> list[str]:
        ids = []
        for row in rows:
            item = deepcopy(row)
            chapter = item.get("chapter")
            if chapter not in self.frame:
                raise ValueError(f"章节不在抽样框内: {chapter}")
            record = self.frame[chapter]
            item.setdefault("work", record.get("work"))
            segment = item.get("segment")
            if segment is not None and record.get("segments") is not None and segment not in record["segments"]:
                raise ValueError(f"段落不在章节登记范围内: {segment}")
            if not item.get("character"):
                raise ValueError("标注缺少人物")
            item["revision"] = int(item.get("revision", 1))
            if item["revision"] < 1:
                raise ValueError("revision 必须为正整数")
            if item.get("mentions", 0) < 0 or item.get("narrative_length", 0) < 0:
                raise ValueError("出场次数与叙事篇幅不能为负")
            self._seq += 1
            item.setdefault("id", f"a{self._seq}")
            self.annotation_store.append(item)
            ids.append(item["id"])
        return ids

    # ---- 分歧查看与裁决 ----

    def disagreements(self) -> list[dict]:
        normalized = canonicalize(self.annotation_store, self.aliases)
        return find_disagreements(normalized, self.adjudications)

    def adjudicate(self, chapter: str, character: str, resolution: dict, editor: str, segment: str | None = None, comment: str | None = None) -> dict:
        canonical = self.aliases.get(character, character)
        key = (chapter, segment, canonical)
        normalized = canonicalize(self.annotation_store, self.aliases)
        known = {
            (row["chapter"], row.get("segment"), row["character"])
            for row in latest_per_annotator(normalized)
        }
        if key not in known:
            raise ValueError("没有可裁决的标注")
        self.adjudications[key] = {
            "appears": resolution.get("appears"),
            "mentions": resolution.get("mentions", 0),
            "narrative_length": resolution.get("narrative_length", 0),
            "editor": editor,
            "comment": comment,
        }
        return deepcopy(self.adjudications[key])

    # ---- 取样方案 ----

    def plan_sample(self, plan_id: str, method: str, works: list[str] | None = None, chapters: list[str] | None = None,
                    strata: dict[str, float] | None = None, groups: list[str] | None = None,
                    segments: list[str] | None = None, seed: int | None = None) -> dict:
        if plan_id in self.plans:
            raise ValueError(f"取样方案编号已存在: {plan_id}")
        for gid in groups or []:
            if gid not in self.registry.groups:
                raise ValueError(f"未登记的亲属组: {gid}")
        plan = build_plan(self.frame, plan_id, method, works=works, chapters=chapters,
                          strata=strata, groups=groups, segments=segments, seed=seed)
        self.plans[plan_id] = plan
        return deepcopy(plan)

    # ---- 长幼位置比较 ----

    def compare(self, group_ids: list[str] | None = None, chapters: set[str] | None = None,
                plan_id: str | None = None, segments: list[str] | None = None,
                note_id: str | None = None, permutations: int = 20000, seed: int = 20261117) -> dict:
        plan = None
        if plan_id is not None:
            if plan_id not in self.plans:
                raise ValueError(f"未登记的取样方案: {plan_id}")
            plan = self.plans[plan_id]
            chapters = set(plan["sampled_chapters"])
            if group_ids is None:
                group_ids = list(plan["groups"])
            if segments is None:
                segments = plan["segments"]
        if not group_ids:
            raise ValueError("比较必须指定已登记的亲属组")
        for gid in group_ids:
            if gid not in self.registry.groups:
                raise ValueError(f"未登记的亲属组: {gid}")
        if chapters is None:
            works = {self.registry.groups[gid]["work"] for gid in group_ids}
            chapters = {c for c, w in self.chapter_work.items() if None in works or w in works}
        chapters = set(chapters)
        if not chapters.issubset(self.frame):
            raise ValueError("分析范围超出登记的章节框")
        result = birth_order_comparison(
            self.annotation_store, self.aliases, self.registry, list(group_ids), chapters,
            plan=plan, segments=segments, adjudications=self.adjudications,
            chapter_work=self.chapter_work, permutations=permutations, seed=seed,
        )
        if note_id is not None:
            note = {
                "kind": "comparison",
                "note_id": note_id,
                "chapters": sorted(chapters),
                "aliases": deepcopy(self.aliases),
                "annotations": deepcopy([r for r in self.annotation_store if r["chapter"] in chapters]),
                "statistics": deepcopy(result),
                "params": {
                    "group_ids": list(group_ids),
                    "chapters": sorted(chapters),
                    "plan_id": plan_id,
                    "segments": list(segments) if segments else None,
                    "permutations": permutations,
                    "seed": seed,
                },
                "excerpts": [],
            }
            self._save_comparison_note(note_id, note)
        return result

    def _save_comparison_note(self, note_id: str, note: dict) -> None:
        existing = self.notes.get(note_id)
        if existing is not None:
            same = (
                existing.get("kind") == "comparison"
                and existing["statistics"] == note["statistics"]
                and existing["params"] == note["params"]
            )
            if not same:
                raise ValueError("研究笔记编号不能复用为不同分析")
            return
        self.notes[note_id] = note

    def compare_scopes(self, group_ids: list[str], scopes: dict[str, set[str]], **kwargs) -> dict:
        """同一比较在多个章节范围下各跑一次，供编辑调整范围查看结论是否改变。"""
        report = {}
        for label, chapters in scopes.items():
            result = self.compare(group_ids, chapters=set(chapters), **kwargs)
            report[label] = {
                "chapter_count": result["scope"]["chapter_count"],
                "assessment": result["assessment"],
                "conclusion": result["conclusion"],
            }
        return report

    # ---- 笔记摘录与失效提示 ----

    def _current_units(self) -> dict:
        normalized = canonicalize(self.annotation_store, self.aliases)
        units, _ = collapse_annotations(normalized, self.adjudications)
        return {(u["chapter"], u.get("segment"), u["character"]): u for u in units}

    def add_excerpt(self, note_id: str, excerpt: dict) -> dict:
        note = self.notes.get(note_id)
        if note is None or note.get("kind") != "comparison":
            raise ValueError("摘录只能加入比较笔记")
        character = self.aliases.get(excerpt["character"], excerpt["character"])
        unit = self._current_units().get((excerpt["chapter"], excerpt.get("segment"), character))
        if unit is None:
            raise ValueError("摘录没有对应的标注证据")
        claim = excerpt.get("claim", {})
        for field in ("appears", "mentions", "narrative_length"):
            if field in claim and claim[field] != unit[field]:
                raise ValueError(f"摘录与当前标注不一致: {field}")
        self._excerpt_seq += 1
        saved = {
            "excerpt_id": f"e{self._excerpt_seq}",
            "character": character,
            "chapter": excerpt["chapter"],
            "segment": excerpt.get("segment"),
            "claim": dict(claim),
            "text": excerpt.get("text"),
            "annotation_ids": list(unit["sources"]),
        }
        note["excerpts"].append(saved)
        return deepcopy(saved)

    def stale_excerpts(self, note_id: str) -> list[dict]:
        """对照当前（含裁决与撤回）的标注，列出已失效的摘录及原因。"""
        note = self.notes[note_id]
        current = self._current_units()
        stale = []
        for excerpt in note.get("excerpts", []):
            key = (excerpt["chapter"], excerpt.get("segment"), excerpt["character"])
            unit = current.get(key)
            if unit is None:
                stale.append({**deepcopy(excerpt), "reason": "对应标注已撤回或不存在，摘录失效"})
                continue
            differences = {
                field: {"摘录": excerpt["claim"].get(field), "当前": unit[field]}
                for field in ("appears", "mentions", "narrative_length")
                if field in excerpt["claim"] and excerpt["claim"][field] != unit[field]
            }
            if differences:
                stale.append({**deepcopy(excerpt), "reason": "裁决或修订改变了标注取值", "differences": differences})
        return stale

    def current_statistics(self, note_id: str) -> dict:
        """按笔记保存的参数，用当前标注与裁决重算统计；已发布笔记保持原样。"""
        note = self.notes.get(note_id)
        if note is None or note.get("kind") != "comparison":
            raise ValueError("该笔记不是比较笔记")
        params = note["params"]
        return self.compare(
            group_ids=params["group_ids"],
            chapters=set(params["chapters"]),
            plan_id=params["plan_id"],
            segments=params["segments"],
            permutations=params["permutations"],
            seed=params["seed"],
        )

    def refresh(self, note_id: str) -> dict:
        """发布口径与当前口径并列，失效摘录明确列出，而不是只刷新总数。"""
        note = self.notes[note_id]
        return {
            "note_id": note_id,
            "published_statistics": deepcopy(note["statistics"]),
            "current_statistics": self.current_statistics(note_id),
            "stale_excerpts": self.stale_excerpts(note_id),
        }
