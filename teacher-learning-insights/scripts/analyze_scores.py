#!/usr/bin/env python3
"""Validate a score long table and produce auditable, per-exam reports.

Only Python's standard library is required. Empty scores are unscored, not zero.
The visible question/student roster comes from the CSV, not an assumed roster.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


REQUIRED = ("exam_id", "student_id", "question_id", "knowledge_point", "score", "max_score")
ZERO = Decimal("0")
ONE = Decimal("1")


class DataError(ValueError):
    """An input violates the documented score contract."""


def number(value: str, field: str, line: int) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise DataError(f"第 {line} 行：{field} 必须为有限数值") from exc
    if not parsed.is_finite():
        raise DataError(f"第 {line} 行：{field} 必须为有限数值")
    try:
        converted = float(parsed)
        if not math.isfinite(converted) or (converted == 0.0 and parsed != ZERO):
            raise DataError(f"第 {line} 行：{field} 超出可报告数值范围")
    except (OverflowError, ValueError) as exc:
        raise DataError(f"第 {line} 行：{field} 超出可报告数值范围") from exc
    return parsed


def numeric(value: Decimal | None) -> float | None:
    if value is None:
        return None
    converted = float(value)
    if not math.isfinite(converted):
        raise DataError("累计数值超出可报告范围，请核对分值单位")
    return round(converted, 6)


def read_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    question_schema: dict[tuple[str, str], tuple[str, Decimal]] = {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            if fields is None:
                raise DataError("CSV 为空，未找到表头")
            if len(fields) != len(set(fields)):
                raise DataError("CSV 表头存在重复列名")
            missing = [name for name in REQUIRED if name not in fields]
            if missing:
                raise DataError("CSV 缺少必需列：" + ", ".join(missing))
            for raw in reader:
                line = reader.line_num
                if None in raw:
                    raise DataError(f"第 {line} 行：存在没有对应列名的额外字段")
                values = {name: (raw.get(name) or "").strip() for name in REQUIRED}
                for name in REQUIRED:
                    if name != "score" and not values[name]:
                        raise DataError(f"第 {line} 行：{name} 不能为空")
                key = (values["exam_id"], values["student_id"], values["question_id"])
                if key in seen:
                    raise DataError(f"第 {line} 行：测验、学生、题号组合重复：{key}")
                seen.add(key)
                maximum = number(values["max_score"], "max_score", line)
                if maximum <= ZERO:
                    raise DataError(f"第 {line} 行：max_score 必须大于零")
                score = number(values["score"], "score", line) if values["score"] else None
                if score is not None and not ZERO <= score <= maximum:
                    raise DataError(f"第 {line} 行：score 必须在 0 与 max_score 之间")
                qkey = (values["exam_id"], values["question_id"])
                schema = (values["knowledge_point"], maximum)
                if qkey in question_schema and question_schema[qkey] != schema:
                    raise DataError(f"第 {line} 行：同一测验同题的知识点或满分不一致：{qkey}")
                question_schema[qkey] = schema
                rows.append({**values, "score": score, "max_score": maximum, "source_line": line})
    except (OSError, UnicodeError, csv.Error) as exc:
        raise DataError(f"无法读取 CSV：{exc}") from exc
    if not rows:
        raise DataError("CSV 没有数据行")
    if not any(row["score"] is not None for row in rows):
        raise DataError("CSV 没有有效评分；空分不能作为零分")
    return rows


def rate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["score"] is not None]
    earned = sum((row["score"] for row in valid), ZERO)
    possible = sum((row["max_score"] for row in valid), ZERO)
    value = earned / possible if possible else None
    return {
        "earned_score": numeric(earned),
        "scored_max_score": numeric(possible),
        "score_rate": numeric(value),
        "scored_responses": len(valid),
        "scored_students": len({row["student_id"] for row in valid}),
    }


def analyze(rows: list[dict[str, Any]], pass_threshold: Decimal = Decimal("0.60"),
            excellent_threshold: Decimal = Decimal("0.85"), aligned_exams: bool = False) -> dict[str, Any]:
    if not (ZERO <= pass_threshold <= excellent_threshold <= ONE):
        raise DataError("阈值须满足 0 ≤ 通过阈值 ≤ 优秀阈值 ≤ 1")
    if not rows or not any(row["score"] is not None for row in rows):
        raise DataError("没有有效评分，无法生成报告")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["exam_id"]].append(row)
    exams: list[dict[str, Any]] = []
    kp_rates: dict[str, list[tuple[str, Decimal]]] = defaultdict(list)
    for exam_id in sorted(grouped):
        current = grouped[exam_id]
        questions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        students: dict[str, list[dict[str, Any]]] = defaultdict(list)
        knowledge: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in current:
            questions[row["question_id"]].append(row)
            students[row["student_id"]].append(row)
            knowledge[row["knowledge_point"]].append(row)
        paper_maximum = sum((items[0]["max_score"] for items in questions.values()), ZERO)
        student_records = []
        complete_scores: list[Decimal] = []
        for student_id in sorted(students):
            items = students[student_id]
            valid = [row for row in items if row["score"] is not None]
            earned = sum((row["score"] for row in valid), ZERO)
            scored_maximum = sum((row["max_score"] for row in valid), ZERO)
            state = "complete" if len(valid) == len(questions) else "partial" if valid else "unscored"
            if state == "complete":
                complete_scores.append(earned)
            student_records.append({
                "student_id": student_id,
                "record_status": state,
                "earned_score": numeric(earned) if valid else None,
                "scored_max_score": numeric(scored_maximum),
                "scored_part_rate": numeric(earned / scored_maximum) if valid else None,
                "full_paper_rate": numeric(earned / paper_maximum) if state == "complete" else None,
                "coverage_rate": numeric(scored_maximum / paper_maximum),
                "scored_questions": len(valid),
                "unscored_questions": len(questions) - len(valid),
                "omitted_question_rows": len(questions) - len(items),
            })
        count = len(complete_scores)
        mean = sum(complete_scores, ZERO) / count if count else None
        passed = sum(score / paper_maximum >= pass_threshold for score in complete_scores)
        excellent = sum(score / paper_maximum >= excellent_threshold for score in complete_scores)
        kp_records = []
        for name in sorted(knowledge):
            items = knowledge[name]
            metrics = rate(items)
            potential = sum((questions[q][0]["max_score"] for q in questions
                             if questions[q][0]["knowledge_point"] == name), ZERO) * len(students)
            maximum = sum((row["max_score"] for row in items if row["score"] is not None), ZERO)
            earned = sum((row["score"] for row in items if row["score"] is not None), ZERO)
            if maximum:
                kp_rates[name].append((exam_id, earned / maximum))
            kp_records.append({"knowledge_point": name, **metrics,
                               "visible_cohort_possible_score": numeric(potential),
                               "coverage_rate": numeric(maximum / potential)})
        question_records = []
        for question_id in sorted(questions):
            items = questions[question_id]
            valid = [row for row in items if row["score"] is not None]
            metrics = rate(items)
            maximum = items[0]["max_score"]
            earned = sum((row["score"] for row in valid), ZERO)
            denominator = maximum * len(valid)
            full = sum(row["score"] == maximum for row in valid)
            zero = sum(row["score"] == ZERO for row in valid)
            question_records.append({
                "question_id": question_id,
                "knowledge_point": items[0]["knowledge_point"],
                "max_score": numeric(maximum), **metrics,
                "score_loss_rate": numeric(ONE - earned / denominator) if valid else None,
                "full_credit_responses": full,
                "full_credit_rate": numeric(Decimal(full) / len(valid)) if valid else None,
                "zero_credit_responses": zero,
                "zero_credit_rate": numeric(Decimal(zero) / len(valid)) if valid else None,
                "unscored_students": len(students) - len(valid),
            })
        exams.append({
            "exam_id": exam_id,
            "paper_max_score": numeric(paper_maximum),
            "visible_questions": len(questions),
            "visible_students": len(students),
            "complete_students": count,
            "partial_students": sum(item["record_status"] == "partial" for item in student_records),
            "unscored_students": sum(item["record_status"] == "unscored" for item in student_records),
            "complete_student_statistics": {
                "mean_score": numeric(mean),
                "mean_rate": numeric(mean / paper_maximum) if mean is not None else None,
                "minimum_score": numeric(min(complete_scores)) if count else None,
                "maximum_score": numeric(max(complete_scores)) if count else None,
                "pass_count": passed if count else None,
                "pass_rate": numeric(Decimal(passed) / count) if count else None,
                "excellent_count": excellent if count else None,
                "excellent_rate": numeric(Decimal(excellent) / count) if count else None,
                "denominator_students": count,
            },
            "scored_response_statistics": rate(current),
            "knowledge_points": kp_records,
            "questions": question_records,
            "students": student_records,
        })
    comparisons = []
    if aligned_exams:
        for name in sorted(kp_rates):
            series = kp_rates[name]
            for previous, following in zip(series, series[1:]):
                comparisons.append({
                    "knowledge_point": name,
                    "from_exam_id": previous[0],
                    "to_exam_id": following[0],
                    "from_score_rate": numeric(previous[1]),
                    "to_score_rate": numeric(following[1]),
                    "difference_percentage_points": numeric((following[1] - previous[1]) * 100),
                    "interpretation": "调用者已声明范围对齐；差值为描述，不能证明试卷等值或干预效果。",
                })
    limitations = [
        "可见学生和题目集合来自 CSV；完全没有数据行的学生或题目无法统计。",
        "空分或缺行都是未评分记录，不能判断缺考，也不以零分补齐。",
        "知识点得分率按有效评分满分加权；不同缺失比例可能改变可比性。",
        "整卷统计仅包含该卷全部可见题目都有评分的学生；部分记录另列。",
        "得分与失分率不能证明错因、学习能力或态度。",
        "各卷按 exam_id 字典序排列，顺序不自动代表日期。",
        "跨卷原始总分不直接比较；相同满分或百分制转换不能证明难度等值。",
    ]
    if not aligned_exams:
        limitations.append("未声明范围、评分和参测条件对齐，未生成跨卷知识点差值。")
    return {
        "schema_version": 1,
        "method_version": "2.0.0",
        "thresholds": {"pass_rate": numeric(pass_threshold), "excellent_rate": numeric(excellent_threshold)},
        "quality": {"input_rows": len(rows), "scored_rows": sum(row["score"] is not None for row in rows),
                    "blank_score_rows": sum(row["score"] is None for row in rows),
                    "validation": "全部数据通过必需列、唯一键、有限值、分值范围与题目一致性核对"},
        "exams": exams,
        "comparisons": {"alignment_declared_by_caller": aligned_exams,
                        "raw_total_scores_comparable": False,
                        "ordering": "exam_id_lexicographic", "knowledge_points": comparisons},
        "limitations": limitations,
    }


def escape(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def percentage(value: float | None) -> str:
    return "未计算" if value is None else f"{value * 100:.2f}%"


def shown(value: Any) -> str:
    if value is None:
        return "未计算"
    if isinstance(value, float):
        return f"{value:g}"
    return escape(value)


def render_markdown(report: dict[str, Any]) -> str:
    quality = report["quality"]
    output = ["# 学情分析报告", "", "本报告只描述可见评分记录，不包含错因或能力判断。", "",
              f"数据检查：{quality['input_rows']} 行，其中有效评分 {quality['scored_rows']} 行，空分 {quality['blank_score_rows']} 行。",
              f"统计设置：通过阈值 {percentage(report['thresholds']['pass_rate'])}；优秀阈值 {percentage(report['thresholds']['excellent_rate'])}。", ""]
    for exam in report["exams"]:
        stats = exam["complete_student_statistics"]
        weighted = exam["scored_response_statistics"]
        output += [f"## 测验 {escape(exam['exam_id'])}", "",
                   f"可见题目 {exam['visible_questions']} 道，满分 {shown(exam['paper_max_score'])}；可见学生 {exam['visible_students']} 人。完整记录 {exam['complete_students']} 人，部分记录 {exam['partial_students']} 人，全未评分 {exam['unscored_students']} 人。", "",
                   "| 完整学生指标 | 数值 |", "|---|---|",
                   f"| 整卷平均分 | {shown(stats['mean_score'])} |",
                   f"| 整卷平均得分率 | {percentage(stats['mean_rate'])} |",
                   f"| 通过人数 / 分母 | {shown(stats['pass_count'])} / {stats['denominator_students']} |",
                   f"| 通过率 | {percentage(stats['pass_rate'])} |",
                   f"| 优秀人数 / 分母 | {shown(stats['excellent_count'])} / {stats['denominator_students']} |",
                   f"| 优秀率 | {percentage(stats['excellent_rate'])} |", "",
                   f"已评分作答加权得分率：{shown(weighted['earned_score'])} / {shown(weighted['scored_max_score'])} = {percentage(weighted['score_rate'])}。此数值含部分记录的已评分题，不能称为全班平均得分率。", "",
                   "### 知识点表现", "", "| 知识点 | 累计得分 / 有效满分 | 得分率 | 有效学生 / 作答条数 | 评分覆盖 |",
                   "|---|---|---|---|---|"]
        for item in exam["knowledge_points"]:
            output.append(f"| {escape(item['knowledge_point'])} | {shown(item['earned_score'])} / {shown(item['scored_max_score'])} | {percentage(item['score_rate'])} | {item['scored_students']} / {item['scored_responses']} | {percentage(item['coverage_rate'])} |")
        output += ["", "### 题目表现", "", "| 题号 | 知识点 | 得分 / 有效满分 | 得分率 | 失分率 | 满分比例 | 零分比例 | 未评分人数 |",
                   "|---|---|---|---|---|---|---|---|"]
        for item in exam["questions"]:
            output.append(f"| {escape(item['question_id'])} | {escape(item['knowledge_point'])} | {shown(item['earned_score'])} / {shown(item['scored_max_score'])} | {percentage(item['score_rate'])} | {percentage(item['score_loss_rate'])} | {percentage(item['full_credit_rate'])} | {percentage(item['zero_credit_rate'])} | {item['unscored_students']} |")
        output += ["", "### 脱敏记录完整度", "", "按学生标识排序，用于教师核对，不是成绩排名。", "",
                   "| 学生标识 | 记录状态 | 已评分得分 / 满分 | 评分覆盖 | 未评分题数 | 完全缺行题数 |",
                   "|---|---|---|---|---|---|"]
        statuses = {"complete": "完整", "partial": "部分", "unscored": "全未评分"}
        for item in exam["students"]:
            output.append(f"| {escape(item['student_id'])} | {statuses[item['record_status']]} | {shown(item['earned_score'])} / {shown(item['scored_max_score'])} | {percentage(item['coverage_rate'])} | {item['unscored_questions']} | {item['omitted_question_rows']} |")
        output.append("")
    output += ["## 跨卷比较", "", "原始总分不直接比较；下列顺序为测验代号字典序，须另行核对日期。", ""]
    comparisons = report["comparisons"]["knowledge_points"]
    if comparisons:
        output += ["调用者声明已对齐考试范围。差值只用于描述，不能证明试卷等值或教学干预效果。", "",
                   "| 知识点 | 起点卷 | 终点卷 | 起点得分率 | 终点得分率 | 差值（百分点） |",
                   "|---|---|---|---|---|---|"]
        for item in comparisons:
            output.append(f"| {escape(item['knowledge_point'])} | {escape(item['from_exam_id'])} | {escape(item['to_exam_id'])} | {percentage(item['from_score_rate'])} | {percentage(item['to_score_rate'])} | {item['difference_percentage_points']:+.2f} |")
    else:
        output.append("没有可报告的跨卷知识点差值；未声明对齐或没有共同的有效评分知识点。")
    output += ["", "## 数据限制", ""]
    output += ["- " + text for text in report["limitations"]]
    return "\n".join(output) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="脱敏的小题成绩长表")
    parser.add_argument("--output-dir", required=True, type=Path, help="report.json 与 report.md 保存目录")
    parser.add_argument("--pass-threshold", default="0.60", help="通过得分率阈值，默认 0.60")
    parser.add_argument("--excellent-threshold", default="0.85", help="优秀得分率阈值，默认 0.85")
    parser.add_argument("--aligned-exams", action="store_true", help="调用者声明考试范围对齐；仅生成描述性知识点差值")
    args = parser.parse_args()
    try:
        pass_threshold = number(args.pass_threshold, "pass-threshold", 0)
        excellent_threshold = number(args.excellent_threshold, "excellent-threshold", 0)
        report = analyze(read_rows(args.input_csv), pass_threshold, excellent_threshold, args.aligned_exams)
        serialized = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        markdown = render_markdown(report)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "report.json").write_text(serialized, encoding="utf-8")
        (args.output_dir / "report.md").write_text(markdown, encoding="utf-8")
    except (DataError, OSError) as exc:
        parser.exit(2, f"数据或输出错误：{exc}\n")
    print(f"已保存：{args.output_dir / 'report.json'}")
    print(f"已保存：{args.output_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
