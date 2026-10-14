#!/usr/bin/env python3
"""Validate exam structure and point allocation; no semantic correctness claims."""

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path


QUESTION_TYPES = ("choice", "short_answer", "worked_response")
DIFFICULTIES = ("easy", "medium", "hard")


def audit_exam(exam):
    """Return a stable report, including every detectable structural error."""
    errors = []

    def error(path, message):
        errors.append({"path": path, "message": message})

    def nonempty(value, path):
        if not isinstance(value, str) or not value.strip():
            error(path, "必须为非空字符串")
            return False
        return True

    def points(value, path, positive=False):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            error(path, "分值必须为数值，不能为布尔值或文本")
            return None
        try:
            number = Decimal(str(value))
        except Exception:
            error(path, "分值无法转换")
            return None
        if not number.is_finite() or number < 0 or (positive and number == 0):
            error(path, "分值必须有限且为正数" if positive else "分值必须有限且非负")
            return None
        return number

    if not isinstance(exam, dict):
        error("$", "试卷必须为 JSON 对象")
        return {"ok": False, "errors": errors, "checks": {}}
    if type(exam.get("schema_version")) is not int or exam["schema_version"] != 1:
        error("schema_version", "只支持整数版本 1")
    for key in ("title", "grade", "subject"):
        nonempty(exam.get(key), key)
    duration = exam.get("duration_minutes")
    if type(duration) is not int or duration <= 0:
        error("duration_minutes", "考试时长必须为正整数分钟")
    target_total = points(exam.get("total_points"), "total_points", positive=True)
    scope = exam.get("scope")
    if not isinstance(scope, list) or not scope:
        error("scope", "范围必须为非空知识点数组")
        scope = []
    for index, item in enumerate(scope):
        nonempty(item, f"scope[{index}]")
    valid_scope = [item for item in scope if isinstance(item, str) and item.strip()]
    if len(valid_scope) != len(set(valid_scope)):
        error("scope", "知识点名称重复")

    blueprint = exam.get("blueprint")
    if not isinstance(blueprint, list) or not blueprint:
        error("blueprint", "细目表必须为非空数组")
        blueprint = []
    cells = {}
    target_sum = Decimal(0)
    for index, cell in enumerate(blueprint):
        path = f"blueprint[{index}]"
        if not isinstance(cell, dict):
            error(path, "细目格必须为对象")
            continue
        cell_id = cell.get("id")
        if not nonempty(cell_id, path + ".id"):
            continue
        if cell_id in cells:
            error(path + ".id", "细目格 ID 重复")
            continue
        cells[cell_id] = cell
        for key in ("knowledge_point", "ability"):
            nonempty(cell.get(key), path + "." + key)
        if cell.get("knowledge_point") not in valid_scope:
            error(path + ".knowledge_point", "知识点不在试卷范围中")
        if cell.get("type") not in QUESTION_TYPES:
            error(path + ".type", "未知题型")
        if cell.get("difficulty") not in DIFFICULTIES:
            error(path + ".difficulty", "未知难度")
        target = points(cell.get("target_points"), path + ".target_points", positive=True)
        if target is not None:
            target_sum += target
    if target_total is not None and target_sum != target_total:
        error("blueprint", f"细目表合计 {target_sum} 与总分 {target_total} 不符")

    questions = exam.get("questions")
    if not isinstance(questions, list) or not questions:
        error("questions", "试题必须为非空数组")
        questions = []
    question_ids = set()
    actual_total = Decimal(0)
    actual_cells = {cell_id: Decimal(0) for cell_id in cells}
    for index, question in enumerate(questions):
        path = f"questions[{index}]"
        if not isinstance(question, dict):
            error(path, "试题必须为对象")
            continue
        question_id = question.get("id")
        if nonempty(question_id, path + ".id"):
            if question_id in question_ids:
                error(path + ".id", "题号重复")
            question_ids.add(question_id)
        nonempty(question.get("stem"), path + ".stem")
        question_type = question.get("type")
        if question_type not in QUESTION_TYPES:
            error(path + ".type", "未知题型")
        if question.get("difficulty") not in DIFFICULTIES:
            error(path + ".difficulty", "未知难度")
        nonempty(question.get("ability"), path + ".ability")
        score = points(question.get("points"), path + ".points", positive=True)
        if score is not None:
            actual_total += score
        nonempty(question.get("answer"), path + ".answer")
        knowledge_points = question.get("knowledge_points")
        if not isinstance(knowledge_points, list) or not knowledge_points:
            error(path + ".knowledge_points", "至少需要一个范围内知识点")
            knowledge_points = []
        valid_tags = []
        for tag_index, tag in enumerate(knowledge_points):
            if nonempty(tag, f"{path}.knowledge_points[{tag_index}]"):
                valid_tags.append(tag)
                if tag not in valid_scope:
                    error(path + ".knowledge_points", f"知识点 {tag} 不在范围内")
        if len(valid_tags) != len(set(valid_tags)):
            error(path + ".knowledge_points", "知识点重复")

        if question_type == "choice":
            options = question.get("options")
            labels, texts = [], []
            if not isinstance(options, list) or len(options) < 2:
                error(path + ".options", "单选题至少要有两个选项")
                options = []
            for option_index, option in enumerate(options):
                opath = f"{path}.options[{option_index}]"
                if not isinstance(option, dict):
                    error(opath, "选项必须为对象")
                    continue
                if nonempty(option.get("label"), opath + ".label"):
                    labels.append(option["label"].strip())
                if nonempty(option.get("text"), opath + ".text"):
                    texts.append(option["text"].strip())
            if len(labels) != len(set(labels)):
                error(path + ".options", "选项标签重复")
            if len(texts) != len(set(texts)):
                error(path + ".options", "选项文本完全重复")
            if question.get("answer") not in labels:
                error(path + ".answer", "单选答案必须恰好对应一个选项标签")

        rubric = question.get("rubric")
        if not isinstance(rubric, list) or not rubric:
            error(path + ".rubric", "评分规则不能为空")
            rubric = []
        rubric_sum = Decimal(0)
        criteria = []
        for rubric_index, item in enumerate(rubric):
            rpath = f"{path}.rubric[{rubric_index}]"
            if not isinstance(item, dict):
                error(rpath, "评分项必须为对象")
                continue
            if nonempty(item.get("criterion"), rpath + ".criterion"):
                criteria.append(item["criterion"].strip())
            item_points = points(item.get("points"), rpath + ".points", positive=True)
            if item_points is not None:
                rubric_sum += item_points
        if len(criteria) != len(set(criteria)):
            error(path + ".rubric", "评分条件重复，可能导致重复给分")
        if score is not None and rubric_sum != score:
            error(path + ".rubric", f"评分项合计 {rubric_sum} 与题分 {score} 不符")

        source = question.get("source")
        if not isinstance(source, dict) or source.get("kind") not in ("original", "authorized"):
            error(path + ".source", "来源类别必须为 original 或 authorized")
        elif source["kind"] == "original":
            nonempty(source.get("note"), path + ".source.note")
        else:
            for key in ("attribution", "locator", "permission_scope", "answer_verification"):
                nonempty(source.get(key), path + ".source." + key)

        allocations = question.get("allocations")
        if not isinstance(allocations, list) or not allocations:
            error(path + ".allocations", "每题必须分配到细目格")
            allocations = []
        allocated_sum = Decimal(0)
        allocated_ids = set()
        for allocation_index, allocation in enumerate(allocations):
            apath = f"{path}.allocations[{allocation_index}]"
            if not isinstance(allocation, dict):
                error(apath, "分配必须为对象")
                continue
            cell_id = allocation.get("cell_id")
            if not nonempty(cell_id, apath + ".cell_id"):
                continue
            if cell_id in allocated_ids:
                error(apath + ".cell_id", "一题内细目格分配重复")
            allocated_ids.add(cell_id)
            allocated = points(allocation.get("points"), apath + ".points", positive=True)
            if allocated is not None:
                allocated_sum += allocated
            if cell_id not in cells:
                error(apath + ".cell_id", "细目格不存在")
                continue
            cell = cells[cell_id]
            if allocated is not None:
                actual_cells[cell_id] += allocated
            for key in ("type", "ability", "difficulty"):
                if question.get(key) != cell.get(key):
                    error(apath + ".cell_id", f"试题 {key} 与细目格不一致")
            if cell.get("knowledge_point") not in valid_tags:
                error(apath + ".cell_id", "细目格知识点不在该题知识点中")
        if score is not None and allocated_sum != score:
            error(path + ".allocations", f"分配合计 {allocated_sum} 与题分 {score} 不符")

    if target_total is not None and actual_total != target_total:
        error("questions", f"题分合计 {actual_total} 与总分 {target_total} 不符")
    for cell_id, cell in cells.items():
        target = cell.get("target_points")
        if isinstance(target, (int, float)) and not isinstance(target, bool) and Decimal(str(target)).is_finite():
            if actual_cells[cell_id] != Decimal(str(target)):
                error("blueprint." + cell_id, f"实际分值 {actual_cells[cell_id]} 与目标 {target} 不符")
    return {
        "ok": not errors,
        "errors": errors,
        "checks": {
            "question_count": len(questions),
            "question_points": str(actual_total),
            "blueprint_points": str(target_sum),
            "cell_points": {key: str(value) for key, value in actual_cells.items()},
        },
        "limits": "仅检查结构、声明字段和分值关系；不证明答案正确、评分互斥、难度准确或来源权限真实。",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exam", type=Path, help="UTF-8 JSON 试卷文件")
    args = parser.parse_args(argv)
    try:
        with args.exam.open(encoding="utf-8") as handle:
            exam = json.load(handle, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        report = audit_exam(exam)
    except (OSError, UnicodeError, ValueError) as exc:
        report = {"ok": False, "errors": [{"path": "$", "message": str(exc)}], "checks": {}}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
