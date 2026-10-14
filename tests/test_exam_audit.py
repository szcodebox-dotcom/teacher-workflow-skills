"""Behavior tests for each independently installable exam auditor."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("teacher-exam-builder", "teacher-blueprint-exam")


class ExamAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = {}
        cls.examples = {}
        for skill in SKILLS:
            script = ROOT / skill / "scripts/audit_exam.py"
            spec = importlib.util.spec_from_file_location(skill.replace("-", "_"), script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls.modules[skill] = module
            cls.examples[skill] = json.loads((ROOT / skill / "references/example-exam.json").read_text(encoding="utf-8"))

    def reports(self, mutate=None):
        for skill in SKILLS:
            exam = copy.deepcopy(self.examples[skill])
            if mutate:
                mutate(exam)
            yield skill, self.modules[skill].audit_exam(exam)

    def assert_rejected(self, mutate, path_fragment):
        for skill, report in self.reports(mutate):
            with self.subTest(skill=skill):
                self.assertFalse(report["ok"])
                self.assertTrue(any(path_fragment in item["path"] for item in report["errors"]), report)

    def test_complete_example_passes_with_expected_totals(self):
        for skill, report in self.reports():
            with self.subTest(skill=skill):
                self.assertTrue(report["ok"], report)
                self.assertEqual(report["checks"]["question_points"], "20")
                self.assertEqual(report["checks"]["cell_points"], {"B1": "4", "B2": "6", "B3": "10"})

    def test_total_mismatch_fails(self):
        self.assert_rejected(lambda exam: exam.update(total_points=25), "questions")

    def test_rubric_mismatch_fails(self):
        self.assert_rejected(lambda exam: exam["questions"][1]["rubric"][0].update(points=3), ".rubric")

    def test_duplicate_rubric_condition_fails(self):
        def mutate(exam):
            exam["questions"][1]["rubric"][1]["criterion"] = exam["questions"][1]["rubric"][0]["criterion"]
        self.assert_rejected(mutate, ".rubric")

    def test_duplicate_question_id_fails(self):
        self.assert_rejected(lambda exam: exam["questions"][1].update(id="Q1"), ".id")

    def test_missing_answer_fails(self):
        self.assert_rejected(lambda exam: exam["questions"][1].pop("answer"), ".answer")

    def test_structural_pass_does_not_prove_semantic_correctness(self):
        for skill, report in self.reports(lambda exam: exam["questions"][1].update(answer="x=999")):
            with self.subTest(skill=skill):
                self.assertTrue(report["ok"])
                self.assertIn("不证明答案正确", report["limits"])

    def test_unknown_choice_answer_fails(self):
        self.assert_rejected(lambda exam: exam["questions"][0].update(answer="E"), ".answer")

    def test_duplicate_choice_text_fails(self):
        def mutate(exam):
            exam["questions"][0]["options"][1]["text"] = exam["questions"][0]["options"][0]["text"]
        self.assert_rejected(mutate, ".options")

    def test_duplicate_choice_label_fails(self):
        self.assert_rejected(lambda exam: exam["questions"][0]["options"][0].update(label="B"), ".options")

    def test_scope_violation_fails(self):
        self.assert_rejected(lambda exam: exam["questions"][1]["knowledge_points"].append("二次方程"), ".knowledge_points")

    def test_blueprint_dimension_mismatch_fails(self):
        self.assert_rejected(lambda exam: exam["questions"][1].update(ability="解释建模"), ".cell_id")

    def test_unknown_cell_fails(self):
        self.assert_rejected(lambda exam: exam["questions"][1]["allocations"][0].update(cell_id="B99"), ".cell_id")

    def test_duplicate_allocation_prevents_double_counting(self):
        def mutate(exam):
            exam["questions"][2]["allocations"].append({"cell_id": "B3", "points": 10})
        self.assert_rejected(mutate, ".allocations")

    def test_valid_multi_knowledge_point_split_passes(self):
        def mutate(exam):
            exam["scope"].append("解释情境结果")
            new_cell = copy.deepcopy(exam["blueprint"][2])
            exam["blueprint"][2]["target_points"] = 6
            new_cell.update(id="B4", knowledge_point="解释情境结果", target_points=4)
            exam["blueprint"].append(new_cell)
            exam["questions"][2]["knowledge_points"].append("解释情境结果")
            exam["questions"][2]["allocations"] = [{"cell_id": "B3", "points": 6}, {"cell_id": "B4", "points": 4}]
        for skill, report in self.reports(mutate):
            with self.subTest(skill=skill):
                self.assertTrue(report["ok"], report)
                self.assertEqual(report["checks"]["question_points"], "20")
                self.assertEqual(report["checks"]["cell_points"]["B4"], "4")

    def test_boolean_points_fail(self):
        self.assert_rejected(lambda exam: exam["questions"][1].update(points=True), ".points")

    def test_nonfinite_points_fail(self):
        self.assert_rejected(lambda exam: exam["questions"][1].update(points=float("nan")), ".points")

    def test_authorized_source_requires_evidence_fields(self):
        self.assert_rejected(lambda exam: exam["questions"][0].update(source={"kind": "authorized"}), ".source.locator")

    def test_malformed_structures_return_errors_without_exception(self):
        broken_values = [None, [], {"scope": [{}], "blueprint": [False, {"id": "B1", "type": []}], "questions": [0, {"type": [], "source": {"kind": []}}]}]
        for skill in SKILLS:
            for value in broken_values:
                with self.subTest(skill=skill, value=value):
                    self.assertFalse(self.modules[skill].audit_exam(value)["ok"])

    def test_decimal_point_totals_are_exact(self):
        for skill in SKILLS:
            exam = copy.deepcopy(self.examples[skill])
            exam["total_points"] = 0.6
            for index, value in enumerate([0.1, 0.2, 0.3]):
                exam["blueprint"][index]["target_points"] = value
                question = exam["questions"][index]
                question["points"] = value
                question["allocations"][0]["points"] = value
                question["rubric"] = [{"criterion": "本题满足所有作答条件", "points": value}]
            with self.subTest(skill=skill):
                report = self.modules[skill].audit_exam(exam)
                self.assertTrue(report["ok"], report)
                self.assertEqual(report["checks"]["question_points"], "0.6")

    def test_cli_exit_codes_and_json_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "bad.json"
            bad.write_text('{"questions":', encoding="utf-8")
            nonfinite = Path(temporary) / "nonfinite.json"
            nonfinite.write_text('{"total_points":NaN}', encoding="utf-8")
            for skill in SKILLS:
                script = ROOT / skill / "scripts/audit_exam.py"
                for path, code in [(ROOT / skill / "references/example-exam.json", 0), (bad, 1), (nonfinite, 1), (Path(temporary) / "missing.json", 1)]:
                    with self.subTest(skill=skill, path=path):
                        result = subprocess.run([sys.executable, str(script), str(path)], capture_output=True, text=True)
                        self.assertEqual(result.returncode, code, result.stderr)
                        self.assertEqual(json.loads(result.stdout)["ok"], code == 0)


if __name__ == "__main__":
    unittest.main()
