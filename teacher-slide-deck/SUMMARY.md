# 可编辑课件 · 2.0.0

**用途：** 将教学内容制作成可编辑 PPTX，逐页附教师讲者备注。

**输入：** 课题、年级、学科或已有教案；可附页数、比例、课时与风格。随包有完整 JSON 示例。

**输出：** PPTX、内容 JSON、教师答案与课堂使用说明。标题、正文、表格均可编辑，练习答案置于备注。

**闭环：** 教学路线 → 完整逐页内容 → JSON 校验 → 生成 PPTX → 结构与视觉检查 → 课堂使用与订正。

**依赖：** Python 3.10+、`python-pptx>=1.0.2,<2.0`；[requirements.txt](requirements.txt) 与 [独立生成器](scripts/build_deck.py) 随包提供。核心生成无需联网素材，无其他技能依赖。可选本地演示文稿渲染工具用于视觉检查。

**示例调用：** `用 $teacher-slide-deck 把五年级数学“平均数”制作成 8 页可编辑 PPTX，每页附讲法、时长和教师答案，并提供内容 JSON。`

**直接运行：** `python3 scripts/build_deck.py references/example-deck.json --output lesson.pptx`（已安装依赖时）。

**现成演示：** [8 页可编辑 PPTX](assets/example-deck.pptx)，附 [全部页面预览](assets/preview.png)。预览使用本地 Hiragino Sans GB 字体替代渲染；PPTX 字体名仍为 Microsoft YaHei，用户可按本机字体修改 JSON 后重新生成。
