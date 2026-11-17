"""章节取样方案：按作品、段落与亲属组制定，保留每章实际入样概率。

- census：全量入样，概率 1.0；
- bernoulli：分层独立 Bernoulli 抽样，记录每层给定概率与种子，可复现；
- convenience：便利选章，无入样概率，结果只能说明所选范围。
"""

import random

METHODS = {"census", "bernoulli", "convenience"}


def build_plan(
    frame: dict[str, dict],
    plan_id: str,
    method: str,
    works: list[str] | None = None,
    chapters: list[str] | None = None,
    strata: dict[str, float] | None = None,
    groups: list[str] | None = None,
    segments: list[str] | None = None,
    seed: int | None = None,
) -> dict:
    if method not in METHODS:
        raise ValueError("未登记的样本选取方式")
    chapter_work = {c: rec.get("work") for c, rec in frame.items()}
    known_works = {w for w in chapter_work.values() if w is not None}

    if method == "convenience":
        if not chapters:
            raise ValueError("便利选取必须给出章节")
        unknown = set(chapters) - set(frame)
        if unknown:
            raise ValueError(f"章节不在抽样框内: {sorted(unknown)}")
        involved = {chapter_work[c] for c in chapters}
        works = sorted(w for w in involved if w is not None)
        pool = [c for c in frame if chapter_work[c] in involved]
        chosen = set(chapters)
        selection = {
            c: {"included": c in chosen, "probability": None, "stratum": chapter_work[c]}
            for c in pool
        }
        probability_based = False
    else:
        if not known_works:
            if works not in (None, [None]):
                raise ValueError("章节框未登记作品")
            works = [None]
        else:
            works = list(works) if works is not None else sorted(known_works)
            unknown = set(works) - known_works
            if unknown:
                raise ValueError(f"作品不在章节框内: {sorted(unknown)}")
        pool = sorted(c for c in frame if chapter_work[c] in works)
        if method == "census":
            selection = {
                c: {"included": True, "probability": 1.0, "stratum": chapter_work[c]}
                for c in pool
            }
        else:
            if not strata:
                raise ValueError("概率抽样必须给出各层入样概率")
            if set(strata) != set(works):
                raise ValueError("分层概率必须覆盖且仅覆盖所选作品")
            for work, p in strata.items():
                if not 0 < float(p) <= 1:
                    raise ValueError("入样概率必须在 (0, 1] 内")
            rng = random.Random(seed)
            selection = {}
            for c in pool:
                p = float(strata[chapter_work[c]])
                selection[c] = {
                    "included": rng.random() < p,
                    "probability": p,
                    "stratum": chapter_work[c],
                }
        probability_based = True

    sampled = sorted(c for c, s in selection.items() if s["included"])
    return {
        "plan_id": plan_id,
        "method": method,
        "works": list(works),
        "groups": list(groups or []),
        "segments": list(segments) if segments else None,
        "seed": seed,
        "probability_based": probability_based,
        "frame_size": len(selection),
        "sampled_chapters": sampled,
        "selection": selection,
    }
