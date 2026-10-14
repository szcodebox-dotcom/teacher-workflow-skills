# 教师工作流专家 · 安装方法

一个专家入口，内置十二套独立技能。专家包版本1.0.0，技能内容基于2.0.0；不需要分别安装十二次。

## 推荐安装：在 WorkBuddy 中完成

1. 下载 `teacher-workflow-expert-v1.0.0.zip`，解压得到 `teacher-workflow-expert` 文件夹。保留 `.codebuddy-plugin` 隐藏目录和完整 `skills` 目录，不要只上传某个 `SKILL.md`。
2. 打开 WorkBuddy，进入「专家·技能·连接器 → 专家 → 我的专家 → 创建专家」。官方创建入口会进入内置专家管理器的对话。
3. 把解压后的目录放入该对话可访问的工作区，或作为文件夹附件提供。复制包内 `安装提示词.txt` 并发送。让 WorkBuddy 根据原包完成校验、复制和注册；不能只生成一个新的同名角色而丢掉十二套技能。
4. 成功后在「我的专家」中选择 **教师工作流专家**，发送下面的安装检查提示词。若列表尚未刷新，重新进入专家页或重启 WorkBuddy 后检查；不能把目录复制成功当作专家注册成功。

```text
请检查当前教师工作流专家是否已注册并可用。定位本专家包的真实目录，读取插件清单，列出十二个技能ID与各自入口；核对所有入口实际存在。再读取 teacher-lesson-plan 的完整示例，用四年级“周长与面积”40分钟课的具体输入，交付完整教案与答案。说明实际读取的文件，不要只复述技能名称或冒称已经运行脚本。
```

完整十二项介绍与36条提示词在 [USAGE.md](USAGE.md)。第一次试用也可直接选择成套备课、教案或学情分析。

## 安装提示词全文

```text
请安装我提供的 teacher-workflow-expert 专家包。先定位解压后的完整目录，读取 INSTALL.md、.codebuddy-plugin/plugin.json 和 agents/teacher-workflow-expert.md。使用你当前 WorkBuddy 内置 expert-manager 校验并注册，保留一个主专家与全部十二个 skills，不重新生成或删减原技能。安装目标是当前 WorkBuddy 配置目录的 plugins/marketplaces/my-experts/plugins/teacher-workflow-expert，注册到 my-experts/.codebuddy-plugin/marketplace.json。先用包内 scripts/verify_package.py 检查完整性，再用 scripts/install_expert.py --dry-run 查看计划与依赖；当前会话具备 CODEBUDDY_SESSION_ID 且官方管理器可用时，执行脚本完成安装和原生注册。需要指定 --manager-dir 时从你当前实际加载的内置管理器路径取得，不猜路径、不伪造会话ID。若已存在同名专家，先说明位置和版本，保留备份，依据我的替换要求处理；不要覆盖其他专家或修改 enabled_plugins.json。完成后回读注册清单、当前会话标记和十二个技能入口，报告实际安装路径并确认能在我的专家中召唤。缺少必要条件时说明具体缺口，不把复制目录称为安装成功。
```

## 安装脚本的用途

从专家包根目录执行；Windows 可把 `python3` 换成 `py -3`。脚本需要 Python 3.11+，只使用标准库。

```bash
python3 scripts/verify_package.py
python3 scripts/install_expert.py --dry-run
```

`--dry-run` 不写配置，列出目标位置、同名冲突、官方管理器位置及当前会话是否可用。以下真正安装命令应由 **WorkBuddy 的创建专家对话**运行：

```bash
python3 scripts/install_expert.py
python3 scripts/install_expert.py --check
```

若需更新同名专家，在明确要替换时使用 `--replace`：原包及注册清单会备份，失败会回滚。`--manager-dir` 接受当前官方 `expert-manager` 技能目录；`--config-dir` 接受当前 WorkBuddy 配置目录，不应指向别的账号或随意指定系统目录。

脚本必须拿到 WorkBuddy **真实当前会话**，不能在其他助手或普通终端伪造 `CODEBUDDY_SESSION_ID`。缺失时会停止真实安装；这不妨碍下载、解压、校验和查看安装计划。

## 使用环境与成品复现

阅读工作流与生成教学文本不要求安装 Python。复现附带脚本需要 Python 3.11+；实际 PPTX 生成还需要 `python-pptx`。建议在解压目录建立独立环境。

macOS / Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-demo.txt
.venv/bin/python scripts/run_examples.py --output-dir ../teacher-expert-demo
```

Windows PowerShell：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-demo.txt
.\.venv\Scripts\python.exe scripts/run_examples.py --output-dir ..\teacher-expert-demo
```

示例会运行两套试卷审计器、学情统计和8页课件生成器，输出实际 JSON、Markdown 和 PPTX；结果来自合成教学样例。PPTX仍须在 PowerPoint/WPS 中目视检查字体与排版，不把结构成功当作课堂效果验证。输出目录须为空，避免覆盖旧成果。

## 专家包与技能包的区别

普通「添加技能 → 上传技能」面向一个 Skill 包，不能据此承诺专家包会自动成为“我的专家”。本包采用官方专家插件结构；本机已安装版本的专家管理器要求复制后注册并带当前会话标记。默认用户目录是 `~/.workbuddy`，以 `WORKBUDDY_CONFIG_DIR` 实际配置为准。

为兼容当前本机官方验证器，插件分类使用 `12-IndustryConsultant`（教育行业顾问），展示名称和十二项教学能力不受影响。官网新版另列出 `15-Education`；需要向新版教育市场提交时可按当时平台规范调整分类并重新验证。此包没有自动上架市场，没有开通外部连接器，不包含凭据或第三方专家正文。

## 官方依据

- [专家包配置规范](https://open.workbuddy.cn/docs/expert)：一个主Agent、内置Skills、双语展示与头像规格。
- [创建与管理专家](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Expert-Center)：客户端创建入口和召唤方法。
- [技能定义规范](https://open.workbuddy.cn/docs/skill)：技能frontmatter与资源结构。

本包的本地验证记录见 [VALIDATION.md](VALIDATION.md)。校验与临时安装测试不等于已在你的 WorkBuddy 会话安装；实际注册由安装过程回读确认。
