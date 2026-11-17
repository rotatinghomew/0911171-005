"""描述统计与亲属组长幼位置比较。"""

import random

from .annotations import canonicalize, collapse_annotations, current_annotations
from .scope import select_scope


def prominence(rows: list[dict], aliases: dict[str, str], chapter_ids: set[str]) -> dict:
    normalized = canonicalize(rows, aliases)
    selected = select_scope(current_annotations(normalized), chapter_ids)
    counts: dict[str, int] = {}
    for row in selected:
        counts[row["character"]] = counts.get(row["character"], 0) + int(row["mentions"])
    return {"chapter_count": len(chapter_ids), "annotation_count": len(selected), "mentions": dict(sorted(counts.items()))}


def _chapter_aggregates(units: list[dict]) -> dict:
    """把证据单元汇总到 人物×章节：同章多段、多行不重复计权。"""
    agg: dict[tuple, dict] = {}
    for unit in units:
        key = (unit["character"], unit["chapter"])
        entry = agg.setdefault(key, {
            "character": unit["character"],
            "chapter": unit["chapter"],
            "appears": False,
            "mentions": 0,
            "narrative_length": 0.0,
            "segments": [],
            "annotation_ids": [],
            "adjudicated": False,
        })
        entry["appears"] = entry["appears"] or bool(unit["appears"])
        entry["mentions"] += int(unit["mentions"])
        entry["narrative_length"] += float(unit["narrative_length"])
        if unit.get("segment") is not None:
            entry["segments"].append(unit["segment"])
        entry["annotation_ids"].extend(unit.get("sources", []))
        entry["adjudicated"] = entry["adjudicated"] or unit.get("adjudicated", False)
    return agg


def _permutation_test(group_values: list[list[tuple]], permutations: int, seed: int) -> dict | None:
    """组内置换检验：最幼位置与其余位置的均值差（单侧，最幼者更多）。

    长幼位置标签在每组内部置换，避免把组间差异当作长幼效应。
    """
    usable = [members for members in group_values if len(members) >= 2]
    if not usable:
        return None

    def statistic(groups: list[list[tuple]]) -> float:
        diffs = []
        for members in groups:
            top = max(b for b, _ in members)
            youngest = [v for b, v in members if b == top]
            others = [v for b, v in members if b != top]
            diffs.append(sum(youngest) / len(youngest) - sum(others) / len(others))
        return sum(diffs) / len(diffs)

    observed = statistic(usable)
    rng = random.Random(seed)
    extreme = 0
    for _ in range(permutations):
        shuffled = []
        for members in usable:
            values = [v for _, v in members]
            rng.shuffle(values)
            shuffled.append(list(zip([b for b, _ in members], values)))
        if statistic(shuffled) >= observed - 1e-12:
            extreme += 1
    return {
        "statistic": "最幼位置均值 - 其余位置均值",
        "observed": observed,
        "p_value": (1 + extreme) / (1 + permutations),
        "permutations": permutations,
        "seed": seed,
        "alternative": "最幼者更多（单侧）",
    }


def birth_order_comparison(
    rows: list[dict],
    aliases: dict[str, str],
    registry,
    group_ids: list[str],
    chapters: set[str],
    plan: dict | None = None,
    segments: set[str] | list[str] | None = None,
    adjudications: dict | None = None,
    chapter_work: dict | None = None,
    permutations: int = 20000,
    seed: int = 20261117,
) -> dict:
    """比较已登记亲属组内各长幼位置的出场与叙事篇幅。

    证据单元为（章节，段落，规范人物），同章多段汇总到人物×章节；
    零出场（已标注但未出场）与未标注分别报告，互不混同。
    """
    chapters = set(chapters)
    chapter_work = chapter_work or {}
    segment_set = set(segments) if segments is not None else None
    normalized = canonicalize(rows, aliases)
    units, unresolved = collapse_annotations(normalized, adjudications)

    def in_scope(unit: dict) -> bool:
        return unit["chapter"] in chapters and (segment_set is None or unit.get("segment") in segment_set)

    scoped = [u for u in units if in_scope(u)]
    unresolved_scoped = [u for u in unresolved if in_scope(u)]
    by_cc = _chapter_aggregates(scoped)

    selection = (plan or {}).get("selection", {})
    probability_based = bool(plan and plan.get("probability_based"))

    def weight_of(chapter: str) -> float:
        if not probability_based:
            return 1.0
        info = selection.get(chapter)
        if not info or not info.get("probability"):
            return 1.0
        return 1.0 / info["probability"]

    char_info: dict[str, tuple] = {}
    for gid in group_ids:
        group = registry.get(gid)
        for member in group["members"]:
            char_info[member["character"]] = (gid, member["birth_order"], group["work"])

    members = []
    positions: dict[int, dict] = {}
    values_length: dict[str, list] = {}
    values_appear: dict[str, list] = {}
    excluded_no_annotation = []
    for character, (gid, order, work) in char_info.items():
        relevant = sorted(c for c in chapters if work is None or chapter_work.get(c) == work)
        annotated = [c for c in relevant if (character, c) in by_cc]
        unannotated = [c for c in relevant if (character, c) not in by_cc]
        appearances = sum(1 for c in annotated if by_cc[(character, c)]["appears"])
        length = sum(by_cc[(character, c)]["narrative_length"] for c in annotated)
        w_appearances = sum(weight_of(c) for c in annotated if by_cc[(character, c)]["appears"])
        w_length = sum(by_cc[(character, c)]["narrative_length"] * weight_of(c) for c in annotated)
        members.append({
            "group": gid,
            "character": character,
            "birth_order": order,
            "annotated_chapters": len(annotated),
            "appearances": appearances,
            "zero_appearances": len(annotated) - appearances,
            "unannotated_chapters": unannotated,
            "narrative_length": length,
            "weighted_narrative_length": w_length,
        })
        pos = positions.setdefault(order, {
            "characters": 0, "annotated_chapters": 0, "appearances": 0,
            "zero_appearances": 0, "unannotated_chapters": 0,
            "narrative_length": 0.0, "weighted_narrative_length": 0.0,
        })
        pos["characters"] += 1
        pos["annotated_chapters"] += len(annotated)
        pos["appearances"] += appearances
        pos["zero_appearances"] += len(annotated) - appearances
        pos["unannotated_chapters"] += len(unannotated)
        pos["narrative_length"] += length
        pos["weighted_narrative_length"] += w_length
        if not annotated:
            excluded_no_annotation.append({"group": gid, "character": character})
        else:
            basis_length = w_length if probability_based else length
            basis_appear = w_appearances if probability_based else appearances
            values_length.setdefault(gid, []).append((order, basis_length))
            values_appear.setdefault(gid, []).append((order, basis_appear))

    positions_out = {}
    for order in sorted(positions):
        pos = positions[order]
        denom = pos["annotated_chapters"]
        positions_out[str(order)] = {
            **pos,
            "mean_narrative_length": pos["narrative_length"] / denom if denom else 0.0,
            "weighted_mean_narrative_length": pos["weighted_narrative_length"] / denom if denom else 0.0,
            "appearance_rate": pos["appearances"] / denom if denom else None,
        }

    drill_down = []
    for (character, chapter), entry in sorted(by_cc.items()):
        if character not in char_info:
            continue
        gid, order, _ = char_info[character]
        drill_down.append({
            "group": gid,
            "character": character,
            "birth_order": order,
            "chapter": chapter,
            **entry,
            "weight": weight_of(chapter),
        })

    test_length = _permutation_test(list(values_length.values()), permutations, seed)
    test_appear = _permutation_test(list(values_appear.values()), permutations, seed)

    studied = set(char_info)
    annotated_any = {chapter for (char, chapter) in by_cc if char in studied}
    wholly_unannotated = sorted(c for c in chapters if c not in annotated_any)

    if plan is not None:
        method = plan["method"]
    elif not chapter_work or chapters == set(chapter_work):
        method = "census"
    else:
        method = "convenience"
    generalizable = {
        "census": "整个章节框（全量，无外推不确定性）",
        "bernoulli": "抽样框（按入样概率加权外推）",
        "convenience": "仅所选章节，不能外推",
    }[method]
    caveats = []
    if method == "convenience":
        caveats.append("便利选章：结果只描述所选章节，不能外推到未选章节。")
    elif method == "bernoulli":
        caveats.append("概率样本：估计按入样概率倒数加权，外推限抽样框内作品；未标注章节不计入零出场。")
    if wholly_unannotated:
        caveats.append(f"范围内 {len(wholly_unannotated)} 章没有任何相关标注；未标注不等于零出场。")
    if unresolved_scoped:
        caveats.append(f"{len(unresolved_scoped)} 处标注分歧未裁决，相关记录未计入统计。")
    if excluded_no_annotation:
        names = "、".join(item["character"] for item in excluded_no_annotation)
        caveats.append(f"以下人物在范围内无标注，未进入置换检验：{names}。")

    if positions_out:
        youngest = max(positions)
        basis = "weighted_mean_narrative_length" if probability_based else "mean_narrative_length"
        leader = max(positions, key=lambda o: positions_out[str(o)][basis])
        youngest_leads = leader == youngest
    else:
        youngest = leader = None
        youngest_leads = False
    p_value = test_length["p_value"] if test_length else None
    if youngest_leads and p_value is not None and p_value <= 0.05:
        assessment = "范围内支持“最小者戏份更多”（组内置换检验显著）；外推范围见不确定性说明。"
    elif youngest_leads:
        assessment = "最小者仅描述性领先，置换检验不显著，不能排除偶然。"
    else:
        assessment = "所选范围不支持“最小者戏份更多”。"

    return {
        "groups": list(group_ids),
        "scope": {
            "chapters": sorted(chapters),
            "chapter_count": len(chapters),
            "segments": sorted(segment_set) if segment_set else None,
        },
        "positions": positions_out,
        "members": members,
        "units": drill_down,
        "unresolved": unresolved_scoped,
        "excluded_no_annotation": excluded_no_annotation,
        "tests": {"narrative_length": test_length, "appearances": test_appear},
        "conclusion": {
            "youngest_position": youngest,
            "length_leader_position": leader,
            "youngest_leads": youngest_leads,
            "p_value": p_value,
        },
        "assessment": assessment,
        "inference": {
            "method": method,
            "generalizable_to": generalizable,
            "frame_size": plan["frame_size"] if plan else (len(chapter_work) if chapter_work else len(chapters)),
            "sampled_chapters": len(chapters),
            "wholly_unannotated_chapters": wholly_unannotated,
            "caveats": caveats,
        },
    }
