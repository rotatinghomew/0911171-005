"""合成数据演示：检视“三兄弟”型故事中“最小者戏份更多”能支持到哪一步。

所有作品、人物、章节与标注均为仓库风格的虚构记录，不含任何文学作品正文。
"""

from .notebook import ResearchNotebook


def build_notebook() -> ResearchNotebook:
    frame = []
    for i in range(1, 9):
        frame.append({"work": "wuling", "chapter": f"w{i:02d}", "segments": ["s1", "s2", "s3"]})
    for i in range(1, 7):
        frame.append({"work": "xichuan", "chapter": f"x{i:02d}", "segments": ["s1", "s2"]})
    notebook = ResearchNotebook(frame)
    notebook.register_aliases({"苇弟": "苇三弟", "阿苇": "苇三弟", "露儿": "露幺"})
    notebook.register_kinship_group("wuling-brothers", [
        {"character": "岩大哥", "birth_order": 1},
        {"character": "澜二哥", "birth_order": 2},
        {"character": "苇三弟", "birth_order": 3},
    ], work="wuling", label="雾岭三兄弟")
    notebook.register_kinship_group("xichuan-brothers", [
        {"character": "峰长子", "birth_order": 1},
        {"character": "岚次子", "birth_order": 2},
        {"character": "露幺", "birth_order": 3},
    ], work="xichuan", label="溪川三兄弟")

    rows = []
    for i in range(1, 9):
        chapter = f"w{i:02d}"
        rows.append({"chapter": chapter, "segment": "s1", "character": "岩大哥",
                     "annotator": "甲", "revision": 1, "mentions": 2, "narrative_length": 40 + i})
        # 澜二哥在 w07 为真实零出场（已标注、未出场），与未标注不同
        second = {"chapter": chapter, "segment": "s2", "character": "澜二哥",
                  "annotator": "甲", "revision": 1, "mentions": 2, "narrative_length": 50 + i}
        if i == 7:
            second.update({"mentions": 0, "narrative_length": 0})
        rows.append(second)
        rows.append({"chapter": chapter, "segment": "s3", "character": "苇弟",
                     "annotator": "甲", "revision": 1, "mentions": 4, "narrative_length": 90 + i})
    # 标注者乙用别名“阿苇”对 w03 给出不同篇幅，构成待裁决分歧
    rows.append({"chapter": "w03", "segment": "s3", "character": "阿苇",
                 "annotator": "乙", "revision": 1, "mentions": 4, "narrative_length": 30})
    for i in range(1, 7):
        chapter = f"x{i:02d}"
        rows.append({"chapter": chapter, "segment": "s1", "character": "峰长子",
                     "annotator": "甲", "revision": 1, "mentions": 2, "narrative_length": 45})
        rows.append({"chapter": chapter, "segment": "s1", "character": "岚次子",
                     "annotator": "乙", "revision": 1, "mentions": 2, "narrative_length": 55})
        rows.append({"chapter": chapter, "segment": "s2", "character": "露儿",
                     "annotator": "甲", "revision": 1, "mentions": 3, "narrative_length": 80})
    notebook.register_annotations(rows)
    return notebook


def main() -> None:
    notebook = build_notebook()

    print("== 待裁决分歧 ==")
    for item in notebook.disagreements():
        values = {row["annotator"]: row["narrative_length"] for row in item["annotations"]}
        print(f"  {item['chapter']} {item['segment']} {item['character']}: {values}")
    notebook.adjudicate("w03", "苇三弟", {"appears": True, "mentions": 4, "narrative_length": 93},
                        editor="编辑A", segment="s3", comment="复核后采纳甲的篇幅")
    print("裁决后剩余分歧:", notebook.disagreements())

    plan = notebook.plan_sample("plan-1", "bernoulli", works=["wuling", "xichuan"],
                                strata={"wuling": 0.75, "xichuan": 0.75},
                                groups=["wuling-brothers", "xichuan-brothers"], seed=3)
    print("\n== 取样方案 plan-1 ==")
    print("  方法:", plan["method"], "抽样框:", plan["frame_size"], "章, 入样:", plan["sampled_chapters"])
    print("  各章入样概率:", {c: s["probability"] for c, s in plan["selection"].items()})

    result = notebook.compare(plan_id="plan-1", note_id="youngest-check", permutations=20000, seed=20261117)
    print("\n== 长幼位置比较（概率样本，加权） ==")
    for order, pos in result["positions"].items():
        print(f"  位置{order}: 出场率 {pos['appearance_rate']:.2f}, "
              f"章均篇幅 {pos['mean_narrative_length']:.1f}, 加权章均 {pos['weighted_mean_narrative_length']:.1f}, "
              f"零出场 {pos['zero_appearances']}, 未标注 {pos['unannotated_chapters']}")
    test = result["tests"]["narrative_length"]
    print("  置换检验: 观测差 %.2f, p=%.4f (%d 次置换)" % (test["observed"], test["p_value"], test["permutations"]))
    print("  评估:", result["assessment"])
    print("  可外推范围:", result["inference"]["generalizable_to"])
    for caveat in result["inference"]["caveats"]:
        print("   -", caveat)

    print("\n== 从比较追到章节与标注（苇三弟） ==")
    for unit in result["units"]:
        if unit["character"] == "苇三弟":
            print(f"  {unit['chapter']} {unit['segments']}: 篇幅 {unit['narrative_length']:.0f}, "
                  f"权重 {unit['weight']:.2f}, 标注 {unit['annotation_ids']}, 裁决={unit['adjudicated']}")

    sampled = result["scope"]["chapters"]
    half = sampled[: max(1, len(sampled) // 2)]
    scopes = notebook.compare_scopes(
        ["wuling-brothers", "xichuan-brothers"],
        {"仅前半样本": set(half), "全部样本": set(sampled)},
        permutations=20000, seed=20261117,
    )
    print("\n== 调整范围查看结论 ==")
    for label, summary in scopes.items():
        print(f"  {label} ({summary['chapter_count']} 章): {summary['assessment']}")

    target = next(u for u in result["units"] if u["character"] == "苇三弟" and u["adjudicated"])
    notebook.add_excerpt("youngest-check", {
        "character": "苇三弟", "chapter": target["chapter"], "segment": target["segments"][0],
        "claim": {"mentions": target["mentions"], "narrative_length": target["narrative_length"]},
        "text": "w03 苇三弟篇幅 93（裁决值）",
    })
    print("\n== 裁决改变后摘录失效提示 ==")
    notebook.adjudicate("w03", "苇三弟", {"appears": True, "mentions": 4, "narrative_length": 30},
                        editor="编辑B", segment="s3", comment="二次复核改采乙的篇幅")
    for stale in notebook.stale_excerpts("youngest-check"):
        print(f"  摘录 {stale['excerpt_id']} 失效: {stale['reason']}, {stale['differences']}")
    refreshed = notebook.refresh("youngest-check")
    print("  发布时位置3章均篇幅: %.1f -> 当前: %.1f" % (
        refreshed["published_statistics"]["positions"]["3"]["mean_narrative_length"],
        refreshed["current_statistics"]["positions"]["3"]["mean_narrative_length"],
    ))
    original = notebook.evidence("youngest-check", "苇三弟")
    print("  已发布笔记仍可回看原始判断 %d 行（含甲乙双方原值）" % len(original))


if __name__ == "__main__":
    main()
