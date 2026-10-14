# 独立解压验证记录

日期：2026-10-14。验证对象：首个 `teacher-workflow-expert-v1.0.0.zip`，SHA-256：`65955ff3731269569b1479c77fb75ad9b94398435015324effd4633f80059c10`。后续仅补验证报告重新打包时，该整包哈希会改变；本记录的内容验证仍针对首次解压载荷。

## 实际执行

- 在独立临时目录解压；ZIP CRC 完整，66 个文件。
- 从解压包执行 `scripts/verify_package.py`：退出 0，12 套技能、65 个载荷文件校验通过。
- 从解压包执行 `scripts/test_install_expert.py`：14 项测试通过；注册器为明确标记的临时测试桩。覆盖已有包保护、替换备份、失败回滚、并发其他注册保留、缺少会话、会话归属标记、路径越界与符号链接。
- 从解压包执行 `scripts/run_examples.py`：两个试卷审计器各校验 3 题共 20 分；学情脚本生成 `report.json` 与 `report.md`；PPTX 生成器输出 8 页可编辑课件，每页有备注，含 1 个可编辑表格。
- 将解压包复制到临时 `WORKBUDDY_CONFIG_DIR/plugins/marketplaces/my-experts/plugins/teacher-workflow-expert`，运行本机 WorkBuddy 内置 **原版** `validate_expert.py`：退出 0，0 错误、0 警告。验证器 SHA-256：`6e85c716af94d6ee2ffc86a24a7230d15cd675a0fbaaf45a8980fd51d9c1c6fd`。

## 额外独立检查

- 用 PyYAML 解析 12 个 `SKILL.md` 和 Agent frontmatter；技能名称与目录一致，版本 2.0.0，中英文描述、作者字段完整；Agent 与插件名称、展示名、职业一致，没有自行声明工具权限。
- 独立计算清单所有哈希：65 项均为 64 个十六进制字符，且与实际文件一致。清单覆盖除 `MANIFEST.json` 自身外所有载荷文件。
- 包中没有 `$teacher-*` 调用语法、作者本机目录或旧 `/tmp` 输出样例；没有保留 Codex 专用 `agents/openai.yaml`。
- Windows 虚拟环境命令出现在安装指南、课件入口与完整示例。工作流封装示例已使用 WorkBuddy 平台边界，没有强制 OpenAI 配置。
- 512×512 PNG 头像已查看，书本和铅笔主体完整，中央构图适合方形展示。

## 验证范围

未读取或写入真实 WorkBuddy 配置，未使用真实会话、未调用原生注册器、未修改解压包源码。本记录证明结构与隔离脚本行为，不宣称已在真实 WorkBuddy 会话召唤。PPTX 已重开核对结构，未逐页渲染；示例与安装器测试数据均为合成材料。

结论：通过。详见 `independent-verification.json`。
