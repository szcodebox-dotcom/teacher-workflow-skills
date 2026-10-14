# 命题与错题工作流审核

审核日期：2026-10-14。范围：原版 `exam-generator`、`chuti-zujuan`、`tizhuang-question-bank`、`cuoti-fast`；新包版本均为 2.0.0。旧目录只读保留，新包正文、教学示例与代码独立编写。

## 原版缺陷与实际升级

| 原工作流 | 可观察缺陷 | 新包及改进 |
|---|---|---|
| exam-generator | 每次先等结构确认；没有机械分值核验；单选唯一性、主观题替代解法与可加总评分不够具体 | `teacher-exam-builder`：直接完成原创整卷，独立求解、逐项判断、评分证据和覆盖分配；附本地 JSON 审计器 |
| chuti-zujuan | “表不定不出卷”及签字把普通请求强制变成审批；没有跨知识点题的计分规则或覆盖差额 | `teacher-blueprint-exam`：仅遵守用户明确提出的先审要求；硬约束核算、稳定细目格、评分点分摊、目标/实际/差额闭环；附独立审计器 |
| tizhuang-question-bank | 未说明实际题源、出处真实性或公开发布权；要求展示第三方完整题干；无 OCR 与缺失答案处理 | `teacher-source-question-bank`：获授权材料台账、来源定位、真实性状态、用途范围、原答案/派生解区分、不确定项隔离和受限正文发布边界 |
| cuoti-fast | 红笔标记直接视为错题；“典型错因”缺少证据区分；只给巩固建议；没有独立复测与后续动作 | `teacher-mistake-coach`：识别证据、观察事实/错因假设/验证问题三分；实际原创巩固题、答案评分、复测、达标回看和未达标新题 |

## 新包可交付资源

四包各自包含 `SKILL.md`、`SUMMARY.md`、`agents/openai.yaml`、`references/worked-example.md`；UI 摘要长度为 25–64 字符，调用示例显式使用各自 `$skill-id`。所有示例标为原创合成，没有虚构真实学校、历史考试、学生数据或学习进步。

原创试卷与细目表组卷各自另带 `scripts/audit_exam.py` 和 `references/example-exam.json`，复制任一技能目录即可运行，不通过仓库根目录或其他技能查找代码。运行只使用 Python 3 标准库。两个包使用同一审计规则的独立副本，以保持单包安装能力。

有据题库案例提供 3 道完整原始题、原答案页、原分值和抽取记录，分值为 6+6+8=20。错题订正案例提供 1 道错题、2 道完整巩固题、2 道完整复测题以及回看/再练的新题；全都有答案与评分，尚未发生的复测结果记为未测。

## 已运行验证

```bash
python3 -m unittest discover -s tests -p test_exam_audit.py -v
python3 teacher-exam-builder/scripts/audit_exam.py teacher-exam-builder/references/example-exam.json
python3 teacher-blueprint-exam/scripts/audit_exam.py teacher-blueprint-exam/references/example-exam.json
```

行为测试：21 个测试通过，每个测试覆盖两个独立副本。包括有效完整试卷、总分不符、评分分项不符、评分条件重复、题号重复、答案缺失、单选未知答案、重复选项、超范围知识点、细目维度不符、未知格、重复分配、合法多知识点分摊、布尔/非有限分值、授权来源缺字段、畸形结构、十进制加总和 CLI 返回码/无效输入。另用故意写错的非空解答演示：结构仍可通过，因此报告明确不证明答案正确。

两个审计器的完整示例均返回 `ok: true`；题数 3、题分合计 20、细目表合计 20，B1/B2/B3 实际分值 4/6/10。失效输入返回错误路径和退出码 1。

系统 `skill-creator/scripts/quick_validate.py` 首次在系统 Python 运行时因缺少 PyYAML 无法启动，随后通过 `uv run --with pyyaml python` 的隔离环境执行，四包均返回 `Skill is valid!`。四份 UI YAML 另经解析，摘要分别为 27、26、27、26 字符，默认提示均包含相应 `$skill-id`。没有全局安装依赖；PyYAML 仅用于技能包验证，不是附带审计器的运行依赖。

## 原创范围与验证限制

独立编写的是新包指令、摘要、示例、评分规则与审计代码；教学目标和常见数学知识本身不具备可证明的全球独占原创性。旧包未被改写后冒充新包的署名来源。审计脚本只检查字段、声明和数值关系，不能证明答案正确、单选语义唯一、评分语义互斥、难度有效或第三方授权真实；这些仍依赖实际独立求解、原件核验与可审阅记录。

本报告没有进行 GitHub 发布、全局安装或外部消息发送；由仓库发布流程统一处理最终公开内容与许可。
