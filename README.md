# 文学标注分析

容器环境固定在仓库 Dockerfile 的 Python 3.11.14 镜像摘要，数值分析依赖与传递依赖在 requirements.txt 中精确锁定。执行 `docker build -t local-analytics .` 后，`docker run --rm --network none local-analytics` 运行内置例子；`docker run --rm --network none local-analytics python -m unittest discover -s tests -v` 运行测试。构建时安装依赖，运行时无需联网；非容器环境使用 Python 3.11，并先执行 `python -m pip install -r requirements.txt`。

仓库内演示数据使用虚构人物与章节记录，不包含《西游记》原文。项目把人物别名、标注版本、样本范围和描述统计分开，供编辑核查研究口径。

运行 `python -m unittest discover -s tests -v`；运行 `python -m literature.demo` 查看合成数据摘要。结果只代表纳入的标注样本。

`literature.notebook.ResearchNotebook` 登记章节框，保存命名研究笔记及其当时使用的标注、别名和章节范围。已有笔记不可被同号替换。选取方式 `census` 表示全框，`convenience` 表示便利选取；没有概率抽样推断能力。标注中的 `revision` 是同一章节、人物记录的版本，`withdrawn` 表示该版本撤回；证据查询返回笔记保存的原始标注行，修订情况应结合行的版本阅读。
