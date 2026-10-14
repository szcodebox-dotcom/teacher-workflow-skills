# WorkBuddy 教师工作流专家 · 安装

这是一个主专家内置十二套技能的完整插件包。专家包1.0.0，教学技能基于2.0.0，MIT许可。

1. [下载专家包 ZIP](https://github.com/szcodebox-dotcom/teacher-workflow-skills/releases/download/workbuddy-v1.0.0/teacher-workflow-expert-v1.0.0.zip)，解压后保留全部目录，特别是隐藏的 `.codebuddy-plugin`。
2. 在 WorkBuddy 打开「专家·技能·连接器 → 专家 → 我的专家 → 创建专家」。把解压后的 `teacher-workflow-expert` 放入该对话工作区或作为文件夹附件提供。
3. 打开包内 `安装提示词.txt`，复制全文发送。要求内置专家管理器依据原包校验、复制、注册，保留十二个技能。安装后在「我的专家」召唤 **教师工作流专家**。

```text
召唤教师工作流专家，为五年级数学“平均数”准备一节40分钟课。
加入3分钟前测，完整交付教案、学案、课堂练习、作业和逐页课件内容，单列教师答案。
再使用内置课件技能生成8页可编辑PPTX、内容JSON和讲者备注；完成文件与答案核对。
```

包内 `INSTALL.md` 有完整安装提示词、更新备份、Windows与macOS命令、依赖处理；`USAGE.md` 有十二项介绍与36条提示词。无需分别安装十二次，不需要外部连接器或API Key。实际文件生成仍取决于当前工具权限和运行环境。

## 核对安装计划

在解压后的专家目录运行：

```bash
python3 scripts/verify_package.py
python3 scripts/install_expert.py --dry-run
```

Windows可用 `py -3`。真正安装应由 WorkBuddy 创建专家对话执行同一脚本；必须取得该平台真实当前会话和官方 `expert-manager`。脚本缺条件时停止，不在普通终端伪造会话。默认不覆盖同名专家；明确要更新时加 `--replace`，保留原插件和注册清单备份，失败恢复本专家而保留其他专家。

## 包结构与验证

```text
teacher-workflow-expert/
├── .codebuddy-plugin/plugin.json
├── agents/teacher-workflow-expert.md
├── avatars/expert.png
├── skills/teacher-*/
├── scripts/install_expert.py
├── scripts/verify_package.py
├── scripts/run_examples.py
├── INSTALL.md
├── USAGE.md
└── MANIFEST.json
```

普通「添加技能 → 上传技能」安装的是Skill，不能据此承诺专家会出现在“我的专家”。[官方客户端文档](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Expert-Center)给出了创建入口；[官方专家规范](https://open.workbuddy.cn/docs/expert)支持一个Agent声明多个Skills。安装目录和注册行为另依据本机官方内置管理器核验。

默认分类为兼容旧版的 `12-IndustryConsultant`（教育行业顾问）；展示名与能力仍为教师工作流专家。新版官方目录提供 `15-Education`，向新版市场提交时按届时规范调整。本次交付是完整安装包，没有上架WorkBuddy市场，也没有代用户全局安装。

## 维护与重新构建

```bash
python -m pip install -r requirements-dev.txt
python scripts/build_workbuddy.py
python dist/workbuddy/teacher-workflow-expert/scripts/verify_package.py
python -B dist/workbuddy/teacher-workflow-expert/scripts/test_install_expert.py
python dist/workbuddy/teacher-workflow-expert/scripts/run_examples.py --output-dir /tmp/workbuddy-demo
```

每次构建从原十二套复制，适配WorkBuddy副本，不改变Codex版的调用配置。ZIP使用一个顶层 `teacher-workflow-expert/` 目录，完整性清单与 `WORKBUDDY-SHA256SUMS` 随发布提供。
