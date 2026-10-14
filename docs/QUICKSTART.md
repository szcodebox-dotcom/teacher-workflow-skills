# 安装与实操

## 运行环境

阅读和使用技能说明不需要 Python。运行附带脚本需要 Python 3.11 或更新版本；课件脚本还需要 python-pptx。学情与试卷脚本使用 Python 标准库。下载仓库后，在仓库根目录执行下面的命令。

## 安装到 Codex

先预览安装计划，再安装全部十二套：

```bash
python3 scripts/install.py --dry-run
python3 scripts/install.py
```

脚本默认安装到 `${CODEX_HOME:-$HOME/.codex}/skills`，安装过程不自动运行教学脚本或安装依赖。已存在的同名目录会停止安装，避免覆盖个人修改。需要替换时明确执行 `python3 scripts/install.py --replace`；原目录自动备份到目标技能目录的上级 `teacher-skill-backups` 中。

只安装一套或选择其他支持文件夹技能的工具：

```bash
python3 scripts/install.py --skill teacher-lesson-pack
python3 scripts/install.py --dest "$HOME/.claude/skills"
```

重启 Codex 以刷新技能列表。在其他工具中，触发方式以该工具实际支持为准；仓库没有宣称已在所有工具上实测。也可直接把所需技能文件夹复制到工具的技能目录，或让助手读取对应 `SKILL.md`。

## 三个完整任务示例

**备课**

```text
使用 $teacher-lesson-pack，为七年级数学“一元一次方程的等式性质”准备一节40分钟新授课。
学生会做整数四则运算，易漏写等式两边的同一步操作。
交付教案、逐页课件内容、学案、两档练习与作业，所有题附答案；直接完成。
```

**原创出卷**

```text
使用 $teacher-exam-builder，生成七年级一元一次方程单元20分钟小测。
总分20分，4道题：2道基础、1道应用、1道解释理由。
不含不等式和方程组，交付学生卷、答案、逐步评分规则和检查结果。
```

**学情跟进**

```text
使用 $teacher-learning-insights 分析我提供的脱敏逐题成绩。
空得分表示未评分，不按0分处理；不要仅凭得分断定学生错因。
然后使用 $teacher-class-action-plan，形成讲评任务、弹性练习和两周复测安排。
```

## 开发校验

创建隔离环境，不修改系统 Python：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/validate_repo.py
python -m unittest discover -s tests -v
python scripts/build_release.py
```

Windows 可使用 `.venv\Scripts\activate` 激活。发布包生成于 `dist/teacher-workflow-skills-v2.0.0.zip`，包含逐文件 `MANIFEST.json`；外部 `SHA256SUMS` 记录整包校验值。旧文件夹、旧 ZIP、旧海报、临时生成结果与凭证不进入发布包。

## 教学使用边界

技能能生成教学产物，不能凭统计图推断心理状况，不能把原创题冒充官方真题，不能把一次合成案例运行称为真实教学效果验证。教材版本、学校模板、真实题干等必要输入缺失时，会说明缺口或采用明确标注的通用设计；不会伪造资料。
