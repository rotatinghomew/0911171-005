# 文学标注分析

容器环境固定在仓库 Dockerfile 的 Python 3.11.14 镜像摘要，数值分析依赖与传递依赖在 requirements.txt 中精确锁定。执行 `docker build -t local-analytics .` 后，`docker run --rm --network none local-analytics` 运行内置例子；`docker run --rm --network none local-analytics python -m unittest discover -s tests -v` 运行测试。构建时安装依赖，运行时无需联网；非容器环境使用 Python 3.11，并先执行 `python -m pip install -r requirements.txt`。

仓库内演示数据使用虚构人物与章节记录，不包含《西游记》原文。项目把人物别名、标注版本、样本范围和描述统计分开，供编辑核查研究口径。

运行 `python -m unittest discover -s tests -v`；运行 `python -m literature.demo` 查看合成数据摘要。结果只代表纳入的标注样本。

`literature.notebook.ResearchNotebook` 登记章节框，保存命名研究笔记及其当时使用的标注、别名和章节范围。已有笔记不可被同号替换。标注中的 `revision` 是同一章节、人物记录的版本，`withdrawn` 表示该版本撤回；`evidence()` 返回笔记保存的原始标注行，修订情况应结合行的版本阅读。

## 亲属组与长幼位置比较

`register_kinship_group` 登记亲属组：成员人物与 `birth_order`（从 1 连续编号），可挂在某部作品上。`compare` 比较组内各长幼位置的出场与叙事篇幅，用于检视“最小者戏份更多”在自己的标注里能支持到哪一步，而不是把外部文章判断当作结论：

- 证据单元为（章节，段落，规范人物）。同一单元的多次标注、多名标注者、同一人物的别名只计一次；同章多段汇总到人物×章节，不能堆叠为独立证据。
- 零出场（已标注但未出场）与未标注分别报告，互不混同；范围内无标注的人物不进置换检验。
- 显著性用组内置换检验（最幼位置与其余位置的均值差，单侧），种子固定、结果可复现。
- 结果中的 `units` 列出每个计数对应的章节、段落、标注编号与是否经裁决，编辑可从一项比较追到相应章节与标注；`compare_scopes` 在多个章节范围下各跑一次，查看结论是否改变。

## 取样方案与入样概率

`plan_sample` 按作品、章节段落和已登记亲属组制定取样方案，并保留每章实际入样概率：

- `census`：全量入样，概率 1.0；`bernoulli`：分层独立抽样，记录每层概率与种子，可复现，比较时按入样概率倒数加权，外推限抽样框内；`convenience`：便利选章，无入样概率，结果只能说明所选范围。
- 比较结果的 `inference` 说明抽样框、入样章数、完全未标注章节与不确定性；便利选章不会被表述为可外推。

## 分歧裁决与摘录失效

两名标注者对同一证据单元取值不同时，`disagreements()` 列出分歧供查看，`adjudicate()` 由编辑裁决；未裁决的分歧不计入统计。统计与编辑引用的证据随裁决一起更新（`current_statistics()` / `refresh()`），已发布笔记保持原样，`evidence()` 仍可回看发布时对应的原始判断。

`add_excerpt()` 把证据摘入比较笔记，摘录须与当前标注一致才能加入。之后裁决改变或标注撤回使摘录不再成立时，`stale_excerpts()` 明确列出失效摘录与原因，`refresh()` 并列发布口径与当前口径，不会只刷新总数却保留不再成立的摘录。
