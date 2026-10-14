"""Behavior tests for missing-score, denominator and comparison semantics."""

import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "teacher-learning-insights" / "scripts" / "analyze_scores.py"
SAMPLE = ROOT / "teacher-learning-insights" / "examples" / "scores.csv"
SPEC = importlib.util.spec_from_file_location("score_analysis", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LearningAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def load(self, records, header=MODULE.REQUIRED, encoding="utf-8"):
        source = self.folder / "scores.csv"
        with source.open("w", encoding=encoding, newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(records)
        return MODULE.read_rows(source)

    def test_reference_sample_completeness_and_weighted_denominators(self):
        report = MODULE.analyze(MODULE.read_rows(SAMPLE))
        self.assertEqual(report["quality"]["input_rows"], 20)
        self.assertEqual(report["quality"]["scored_rows"], 14)
        self.assertEqual(report["quality"]["blank_score_rows"], 6)
        e1 = report["exams"][0]
        self.assertEqual((e1["complete_students"], e1["partial_students"], e1["unscored_students"]), (2, 1, 1))
        stats = e1["complete_student_statistics"]
        self.assertEqual(stats["mean_score"], 5.5)
        self.assertEqual(stats["pass_rate"], 0.5)
        self.assertEqual(stats["excellent_rate"], 0.0)
        fractions = next(item for item in e1["knowledge_points"] if item["knowledge_point"] == "分数计算")
        self.assertEqual((fractions["earned_score"], fractions["scored_max_score"]), (7.0, 14.0))
        self.assertEqual(fractions["score_rate"], 0.5)
        self.assertAlmostEqual(fractions["coverage_rate"], 14 / 24, places=6)
        self.assertEqual(e1["scored_response_statistics"]["earned_score"], 16.0)
        self.assertEqual(e1["scored_response_statistics"]["scored_max_score"], 26.0)
        e2_stats = report["exams"][1]["complete_student_statistics"]
        self.assertEqual(e2_stats["pass_count"], 1)
        self.assertAlmostEqual(e2_stats["pass_rate"], 1 / 3, places=6)

    def test_multi_student_multi_question_weights_not_mean_of_percentages(self):
        rows = self.load([
            ["E", "A", "Q1", "K", "1", "1"],
            ["E", "B", "Q1", "K", "1", "1"],
            ["E", "A", "Q2", "K", "0", "9"],
            ["E", "B", "Q2", "K", "", "9"],
        ])
        kp = MODULE.analyze(rows)["exams"][0]["knowledge_points"][0]
        self.assertEqual((kp["earned_score"], kp["scored_max_score"]), (2, 11))
        self.assertAlmostEqual(kp["score_rate"], 2 / 11, places=6)
        self.assertNotEqual(kp["score_rate"], 0.5)
        self.assertEqual(kp["scored_responses"], 3)
        self.assertEqual(kp["scored_students"], 2)

    def test_omitted_question_row_marks_partial_without_imputing_zero(self):
        rows = self.load([
            ["E", "A", "Q1", "K", "2", "2"],
            ["E", "A", "Q2", "K", "4", "4"],
            ["E", "B", "Q1", "K", "1", "2"],
        ])
        exam = MODULE.analyze(rows)["exams"][0]
        student = exam["students"][1]
        self.assertEqual(student["record_status"], "partial")
        self.assertEqual(student["omitted_question_rows"], 1)
        self.assertEqual(student["scored_part_rate"], 0.5)
        self.assertIsNone(student["full_paper_rate"])
        self.assertEqual(exam["complete_student_statistics"]["mean_score"], 6)
        self.assertEqual(exam["questions"][1]["unscored_students"], 1)

    def test_zero_is_valid_and_blank_is_not_zero(self):
        rows = self.load([["E", "A", "Q", "K", "0", "4"], ["E", "B", "Q", "K", "", "4"]])
        exam = MODULE.analyze(rows)["exams"][0]
        self.assertEqual(exam["complete_students"], 1)
        self.assertEqual(exam["unscored_students"], 1)
        self.assertEqual(exam["questions"][0]["scored_max_score"], 4)
        self.assertEqual(exam["questions"][0]["zero_credit_rate"], 1)
        self.assertEqual(exam["complete_student_statistics"]["mean_score"], 0)

    def test_no_complete_students_reports_null_full_paper_metrics(self):
        rows = self.load([
            ["E", "A", "Q1", "K", "1", "2"],
            ["E", "A", "Q2", "K", "", "2"],
            ["E", "B", "Q1", "K", "", "2"],
            ["E", "B", "Q2", "K", "1", "2"],
        ])
        report = MODULE.analyze(rows)
        stats = report["exams"][0]["complete_student_statistics"]
        self.assertEqual(stats["denominator_students"], 0)
        self.assertIsNone(stats["mean_score"])
        self.assertIsNone(stats["pass_rate"])
        self.assertIsNone(stats["pass_count"])
        self.assertIn("未计算", MODULE.render_markdown(report))

    def test_unscored_exam_remains_visible_when_other_exam_has_valid_data(self):
        rows = self.load([["E1", "A", "Q", "K", "", "2"], ["E2", "A", "Q", "K", "1", "2"]])
        exams = MODULE.analyze(rows)["exams"]
        self.assertEqual(len(exams), 2)
        self.assertEqual(exams[0]["unscored_students"], 1)
        self.assertIsNone(exams[0]["knowledge_points"][0]["score_rate"])

    def test_score_loss_is_not_zero_credit_student_ratio(self):
        e1 = MODULE.analyze(MODULE.read_rows(SAMPLE))["exams"][0]
        q2 = next(item for item in e1["questions"] if item["question_id"] == "Q2")
        self.assertEqual(q2["score_loss_rate"], 0.75)
        self.assertEqual(q2["zero_credit_rate"], 0.5)
        self.assertEqual(q2["full_credit_rate"], 0.0)

    def test_different_paper_maxima_never_enable_raw_score_comparison(self):
        report = MODULE.analyze(MODULE.read_rows(SAMPLE))
        self.assertEqual([item["paper_max_score"] for item in report["exams"]], [10, 12])
        self.assertFalse(report["comparisons"]["raw_total_scores_comparable"])
        self.assertEqual(report["comparisons"]["knowledge_points"], [])
        self.assertFalse(report["comparisons"]["alignment_declared_by_caller"])

    def test_declared_alignment_returns_only_descriptive_common_knowledge_differences(self):
        report = MODULE.analyze(MODULE.read_rows(SAMPLE), aligned_exams=True)
        comparisons = {item["knowledge_point"]: item for item in report["comparisons"]["knowledge_points"]}
        self.assertEqual(comparisons["分数计算"]["difference_percentage_points"], 25)
        self.assertAlmostEqual(comparisons["应用表达"]["difference_percentage_points"], -100 / 6, places=6)
        self.assertEqual(comparisons["分数计算"]["from_exam_id"], "E1")
        self.assertEqual(comparisons["分数计算"]["to_exam_id"], "E2")
        self.assertFalse(report["comparisons"]["raw_total_scores_comparable"])
        self.assertIn("不能证明", comparisons["分数计算"]["interpretation"])

    def test_duplicate_student_question_is_rejected_even_if_one_score_is_blank(self):
        with self.assertRaisesRegex(MODULE.DataError, "组合重复"):
            self.load([["E", "A", "Q", "K", "", "4"], ["E", "A", "Q", "K", "2", "4"]])

    def test_invalid_score_and_maximum_are_rejected(self):
        for score, maximum in [("-1", "4"), ("5", "4"), ("1", "0"), ("1", "-2"), ("NaN", "4"), ("Infinity", "4"), ("1", "NaN")]:
            with self.subTest(score=score, maximum=maximum):
                with self.assertRaises(MODULE.DataError):
                    self.load([["E", "A", "Q", "K", score, maximum]])

    def test_missing_knowledge_point_is_not_inferred(self):
        with self.assertRaisesRegex(MODULE.DataError, "knowledge_point 不能为空"):
            self.load([["E", "A", "Q", "", "1", "2"]])

    def test_inconsistent_question_schema_is_rejected(self):
        for knowledge, maximum in [("K", "3"), ("OTHER", "2")]:
            with self.subTest(knowledge=knowledge, maximum=maximum):
                with self.assertRaisesRegex(MODULE.DataError, "不一致"):
                    self.load([["E", "A", "Q", "K", "1", "2"], ["E", "B", "Q", knowledge, "1", maximum]])

    def test_no_effective_data_is_rejected(self):
        for records in [[], [["E", "A", "Q", "K", "", "4"]]]:
            with self.subTest(records=records):
                with self.assertRaises(MODULE.DataError):
                    self.load(records)

    def test_missing_and_duplicate_headers_are_rejected(self):
        with self.assertRaisesRegex(MODULE.DataError, "缺少必需列"):
            self.load([], header=("exam_id", "student_id"))
        with self.assertRaisesRegex(MODULE.DataError, "重复列名"):
            self.load([], header=MODULE.REQUIRED + ("score",))

    def test_bom_and_decimal_scores_are_supported(self):
        rows = self.load([["E", "A", "Q", "K", "0.1", "0.3"], ["E", "B", "Q", "K", "0.2", "0.3"]], encoding="utf-8-sig")
        metric = MODULE.analyze(rows)["exams"][0]["knowledge_points"][0]
        self.assertEqual(metric["earned_score"], 0.3)
        self.assertEqual(metric["scored_max_score"], 0.6)
        self.assertEqual(metric["score_rate"], 0.5)

    def test_threshold_boundaries_are_inclusive_and_configuration_is_checked(self):
        rows = self.load([["E", "A", "Q", "K", "6", "10"], ["E", "B", "Q", "K", "8.5", "10"]])
        stats = MODULE.analyze(rows)["exams"][0]["complete_student_statistics"]
        self.assertEqual(stats["pass_count"], 2)
        self.assertEqual(stats["excellent_count"], 1)
        with self.assertRaises(MODULE.DataError):
            MODULE.analyze(rows, Decimal("0.9"), Decimal("0.8"))

    def test_cli_writes_json_and_markdown(self):
        destination = self.folder / "output"
        process = subprocess.run([sys.executable, str(SCRIPT), str(SAMPLE), "--output-dir", str(destination)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads((destination / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["quality"]["scored_rows"], 14)
        markdown = (destination / "report.md").read_text(encoding="utf-8")
        self.assertIn("7 / 14", markdown)
        self.assertIn("全未评分", markdown)
        self.assertNotIn("缺考人数", markdown)

    def test_cli_invalid_input_creates_no_report(self):
        source = self.folder / "invalid.csv"
        source.write_text("exam_id,student_id,question_id,knowledge_point,score,max_score\nE,A,Q,K,5,4\n", encoding="utf-8")
        destination = self.folder / "invalid-output"
        process = subprocess.run([sys.executable, str(SCRIPT), str(source), "--output-dir", str(destination)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 2)
        self.assertIn("score 必须", process.stderr)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
