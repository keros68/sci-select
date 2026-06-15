import inspect
import importlib
import unittest

import scripts.journal_metrics as metrics
selector = importlib.import_module("scripts.select_journals")
from scripts.select_journals import (
    infer_paper_profile,
    rank_metric_records,
    format_selection_report,
    format_selection_matrix,
    interleave_candidate_groups,
    assign_submission_bands,
)


class SciSelectTests(unittest.TestCase):
    def test_infers_english_groundwater_isotope_categories(self):
        profile = infer_paper_profile(
            "Groundwater nitrate source identification using stable isotopes "
            "and hydrochemistry in an agricultural watershed."
        )

        categories = {(c["category1"], c["category2"]) for c in profile["categories"]}

        self.assertIn(("环境科学与生态学", "水资源"), categories)
        self.assertIn(("地球科学", "地球化学与地球物理"), categories)
        self.assertNotEqual(
            profile["categories"],
            [{"category1": "环境科学与生态学", "category2": "环境科学"}],
        )

    def test_infers_medical_ai_categories(self):
        profile = infer_paper_profile(
            "A deep learning radiomics model predicts lung cancer prognosis "
            "from CT imaging and clinical records."
        )

        categories = {(c["category1"], c["category2"]) for c in profile["categories"]}

        self.assertIn(("医学", "肿瘤学"), categories)
        self.assertIn(("计算机科学", "计算机：人工智能"), categories)

    def test_applied_method_terms_do_not_dominate_domain_terms(self):
        profile = infer_paper_profile(
            "Machine learning model for crop irrigation scheduling in agricultural farmland."
        )

        categories = [(c["category1"], c["category2"]) for c in profile["categories"]]

        self.assertEqual(categories[0], ("农林科学", "农业综合"))
        self.assertNotEqual(categories[0], ("计算机科学", "计算机：人工智能"))
        self.assertIn("machine learning", profile["methods"])

    def test_ranking_uses_fit_quality_and_risk_flags(self):
        profile = infer_paper_profile(
            "Groundwater nitrate source identification using stable isotopes "
            "and hydrochemistry in an agricultural watershed."
        )
        records = [
            {
                "name": "Journal of Hydrology",
                "impact_factor": "6.3",
                "partition": "1区",
                "sci_type": "SCIE",
                "h_index": 198,
                "field": "水资源; 地球化学与地球物理",
                "speed": "网友分享经验：平均8.3个月",
                "_sources": ["letpub", "openalex"],
            },
            {
                "name": "Broad Environmental Letters",
                "impact_factor": "8.0",
                "partition": "1区",
                "sci_type": "SCIE",
                "h_index": 80,
                "field": "环境科学",
                "_sources": ["letpub", "openalex"],
            },
            {
                "name": "Emerging Water Reports",
                "impact_factor": "2.1",
                "partition": "4区",
                "sci_type": "ESCI",
                "field": "水资源",
                "_sources": ["letpub"],
                "_source_errors": {"openalex": "timeout"},
            },
        ]

        ranked = rank_metric_records(profile, records)

        self.assertEqual(ranked[0]["name"], "Journal of Hydrology")
        self.assertEqual(ranked[0]["tier"], "推荐")
        self.assertEqual(ranked[-1]["tier"], "谨慎")
        self.assertIn("OpenAlex未获取", ranked[-1]["data_notes"])

    def test_report_does_not_expose_login_or_comment_flow(self):
        profile = infer_paper_profile("groundwater isotope hydrochemistry")
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "Journal of Hydrology",
                    "impact_factor": "6.3",
                    "partition": "1区",
                    "sci_type": "SCIE",
                    "field": "水资源; 地球化学与地球物理",
                    "_sources": ["letpub"],
                    "_source_errors": {"openalex": "SSL error"},
                }
            ],
        )

        report = format_selection_report(profile, ranked)

        self.assertIn("sci-select", report)
        self.assertIn("OpenAlex未获取", report)
        self.assertNotIn("评论", report)
        self.assertNotIn("登录", report)
        self.assertNotIn("cookie", report.lower())
        self.assertNotIn("comments_mode", inspect.signature(selector.select_journals).parameters)

    def test_openalex_source_matching_rejects_unrelated_name(self):
        source = {
            "display_name": "Journal of Hydrology",
            "issn_l": "0022-1694",
            "issn": ["0022-1694"],
        }

        self.assertTrue(metrics._openalex_source_matches(source, "Journal of Hydrology"))
        self.assertTrue(metrics._openalex_source_matches(source, "J Hydrol", "00221694"))
        self.assertFalse(metrics._openalex_source_matches(source, "Nature"))

    def test_openalex_source_matching_handles_missing_lists(self):
        source = {
            "display_name": "Journal of Hydrology",
            "issn_l": None,
            "issn": None,
            "alternate_titles": None,
        }

        self.assertTrue(metrics._openalex_source_matches(source, "Journal of Hydrology"))

    def test_known_removed_wos_journal_overrides_stale_scie_status(self):
        record = {
            "name": "Science of the Total Environment",
            "sci_type": "SCIE",
            "warning": False,
            "_sources": ["letpub"],
        }

        metrics._apply_known_status_overrides(record)

        self.assertEqual(record["wos_status"], "removed")
        self.assertEqual(record["sci_type"], "WOS_REMOVED")
        self.assertTrue(record["warning"])
        self.assertIn("WoS已移除", metrics.format_metrics_line(record))

    def test_removed_wos_status_is_not_recommended(self):
        profile = infer_paper_profile("environmental pollution water quality")
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "Science of the Total Environment",
                    "impact_factor": "8.0",
                    "partition": "1区",
                    "sci_type": "WOS_REMOVED",
                    "wos_status": "removed",
                    "field": "环境科学; 水资源",
                    "_sources": ["letpub"],
                }
            ],
        )

        self.assertEqual(ranked[0]["tier"], "不推荐")
        self.assertIn("Web of Science", "；".join(ranked[0]["risk_reasons"]))

    def test_matrix_report_shows_decision_table(self):
        profile = infer_paper_profile("groundwater isotope hydrochemistry")
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "Journal of Hydrology",
                    "impact_factor": "6.3",
                    "partition": "1区",
                    "sci_type": "SCIE",
                    "field": "水资源; 地球化学与地球物理",
                    "speed": "网友分享经验：平均8.3个月",
                    "_sources": ["letpub", "openalex"],
                    "h_index": 198,
                    "is_oa": False,
                }
            ],
        )

        matrix = format_selection_matrix(profile, ranked)

        self.assertIn("| 期刊 | 建议 | 主题匹配 |", matrix)
        self.assertIn("Journal of Hydrology", matrix)
        self.assertIn("SCIE", matrix)
        self.assertIn("平均8.3个月", matrix)

    def test_candidate_groups_are_interleaved_across_categories(self):
        groups = [
            [{"name": "Water A"}, {"name": "Water B"}, {"name": "Water C"}],
            [{"name": "Geochem A"}, {"name": "Geochem B"}],
            [{"name": "Geology A"}],
        ]

        candidates = interleave_candidate_groups(groups, limit=5)

        self.assertEqual(
            [c["name"] for c in candidates],
            ["Water A", "Geochem A", "Geology A", "Water B", "Geochem B"],
        )

    def test_review_journal_is_cautious_for_non_review_paper(self):
        profile = infer_paper_profile("groundwater nitrate hydrochemistry field sampling")
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "REVIEWS OF GEOPHYSICS",
                    "impact_factor": "37.3",
                    "partition": "1区",
                    "sci_type": "SCIE",
                    "field": "地球化学与地球物理",
                    "_sources": ["letpub", "openalex"],
                }
            ],
        )

        self.assertEqual(ranked[0]["tier"], "谨慎")
        self.assertIn("综述型期刊", "；".join(ranked[0]["risk_reasons"]))

    def test_submission_bands_cover_ambition_solid_and_safe_options(self):
        profile = infer_paper_profile("groundwater nitrate hydrochemistry")
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "Ambition Journal",
                    "impact_factor": "12",
                    "partition": "1区",
                    "sci_type": "SCIE",
                    "field": "水资源",
                    "_sources": ["letpub"],
                },
                {
                    "name": "Solid Journal",
                    "impact_factor": "5.5",
                    "partition": "2区",
                    "sci_type": "SCIE",
                    "field": "水资源",
                    "_sources": ["letpub"],
                },
                {
                    "name": "Safe Journal",
                    "impact_factor": "3.2",
                    "partition": "3区",
                    "sci_type": "SCIE",
                    "field": "水资源",
                    "_sources": ["letpub"],
                },
            ],
        )

        banded = assign_submission_bands(ranked)
        report = format_selection_report(profile, banded)

        self.assertEqual([item["submission_band"] for item in banded], ["冲刺", "稳妥", "保底"])
        self.assertIn("未提供全文质量评价", report)
        self.assertIn("冲刺", report)
        self.assertIn("稳妥", report)
        self.assertIn("保底", report)


if __name__ == "__main__":
    unittest.main()
