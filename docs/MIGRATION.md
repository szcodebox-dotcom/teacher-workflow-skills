# 从初版升级到 2.0

新版使用专属 `teacher-` 命名，避免与系统级 `skill-creator`、通用 `find-skills` 和其他来源的技能同名。旧包不需要覆盖或改名；可先安装新版后按新名称调用。

| 初版目录 | 新版目录 / 调用名 | 定位 |
|---|---|---|
| `lesson-pack` | [teacher-lesson-pack](../teacher-lesson-pack/SUMMARY.md) | 成套备课 |
| `k12-lesson-design` | [teacher-lesson-plan](../teacher-lesson-plan/SUMMARY.md) | 教案设计 |
| `office-kejian` | [teacher-slide-deck](../teacher-slide-deck/SUMMARY.md) | 可编辑课件 |
| `exam-generator` | [teacher-exam-builder](../teacher-exam-builder/SUMMARY.md) | 原创试卷 |
| `chuti-zujuan` | [teacher-blueprint-exam](../teacher-blueprint-exam/SUMMARY.md) | 细目表组卷 |
| `tizhuang-question-bank` | [teacher-source-question-bank](../teacher-source-question-bank/SUMMARY.md) | 有据题库 |
| `cuoti-fast` | [teacher-mistake-coach](../teacher-mistake-coach/SUMMARY.md) | 错题订正 |
| `xueqing-analysis` | [teacher-learning-insights](../teacher-learning-insights/SUMMARY.md) | 学情分析 |
| `class-analysis-junior` | [teacher-class-action-plan](../teacher-class-action-plan/SUMMARY.md) | 班级跟进 |
| `yureka-lab-edu` | [teacher-communication-studio](../teacher-communication-studio/SUMMARY.md) | 教学沟通 |
| `find-skills` | [teacher-workflow-router](../teacher-workflow-router/SUMMARY.md) | 工作流导航 |
| `skill-creator` | [teacher-workflow-maker](../teacher-workflow-maker/SUMMARY.md) | 工作流封装 |

初版 ZIP 和海报不代表 2.0 内容。本地初版已备份到发布目录之外，新版打包采用显式文件清单，不会把旧包混入。

如果以前安装了通用 `find-skills` 或 `skill-creator`，保留原有安装；新版导航和教学流程封装只覆盖本教师工作流域。
