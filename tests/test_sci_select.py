import inspect
import importlib
import unittest

import scripts.journal_metrics as metrics
import scripts.letpub_client as letpub
selector = importlib.import_module("scripts.select_journals")
from scripts.select_journals import (
    infer_paper_profile,
    rank_metric_records,
    format_selection_report,
    format_selection_matrix,
    interleave_candidate_groups,
    assign_submission_bands,
)
from scripts.official_finders import build_finder_checklist, format_finder_checklist


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

    def test_letpub_detail_extracts_public_xinrui_partition(self):
        html = """
        <table>
          <tr>
            <td>《新锐期刊分区表》 （ 2026年3月发布 ）</td>
            <td>趋势图</td>
            <td>地球科学 3区 1区 4区</td>
            <td>WATER RESOURCES 水资源 2区 3区 1区</td>
            <td>WATER RESOURCES 水资源</td>
            <td>2区 3区 1区</td>
            <td>是</td>
            <td>N/A</td>
            <td>期刊分区表 （ 2025年3月升级版 ）</td>
            <td>地球科学 3区 1区 4区</td>
            <td>WATER RESOURCES 水资源 4区 2区 1区</td>
            <td>是</td>
            <td>否</td>
          </tr>
        </table>
        """

        detail = letpub.parse_detail_page(html)

        self.assertEqual(detail["xinrui_partition_2026"], "3区")
        self.assertEqual(detail["xinrui_2026"]["分区"], "3区")
        self.assertTrue(detail["xinrui_2026"]["Top期刊"])
        self.assertFalse(detail["xinrui_2026"]["综述期刊"])

    def test_metrics_prefers_letpub_xinrui_before_api_lookup(self):
        letpub_detail = {
            "issn": "0022-1694",
            "impact_factor": "6.3",
            "ch_sci_2025": {"分区": "1区"},
            "xinrui_partition_2026": "3区",
        }

        result = metrics._merge_letpub_metrics({"name": "Journal of Hydrology", "_sources": []}, letpub_detail)

        self.assertEqual(result["cas_partition_2025"], "1区")
        self.assertEqual(result["xinrui_partition_2026"], "3区")

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

    def test_metrics_line_labels_2025_cas_and_2026_xinrui_partitions(self):
        line = metrics.format_metrics_line(
            {
                "name": "Journal of Hydrology",
                "sci_type": "SCIE",
                "impact_factor": "6.3",
                "cas_partition_2025": "1区",
                "xinrui_partition_2026": "2区Top",
            }
        )

        self.assertIn("2025中科院=1区", line)
        self.assertIn("2026新锐=2区Top", line)
        self.assertNotIn("分区=1区", line)

    def test_matrix_report_shows_cas_2025_and_xinrui_2026_columns(self):
        profile = infer_paper_profile("groundwater isotope hydrochemistry")
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "Journal of Hydrology",
                    "impact_factor": "6.3",
                    "cas_partition_2025": "1区",
                    "xinrui_partition_2026": "2区Top",
                    "sci_type": "SCIE",
                    "field": "水资源; 地球化学与地球物理",
                    "_sources": ["letpub", "openalex", "xinrui"],
                }
            ],
        )

        matrix = format_selection_matrix(profile, ranked)

        self.assertIn("| 期刊 | 建议 | 主题匹配 | 梯度 | IF | 2025中科院 | 2026新锐 | 收录 |", matrix)
        self.assertIn("| Journal of Hydrology |", matrix)
        self.assertIn("| 1区 | 2区Top | SCIE |", matrix)

    def test_letpub_xinrui_partition_is_not_reported_missing(self):
        profile = infer_paper_profile("groundwater isotope hydrochemistry")
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "Journal of Hydrology",
                    "impact_factor": "6.3",
                    "cas_partition_2025": "1区",
                    "xinrui_partition_2026": "3区",
                    "sci_type": "SCIE",
                    "field": "水资源; 地球化学与地球物理",
                    "_sources": ["letpub", "openalex"],
                }
            ],
        )

        self.assertNotIn("2026新锐分区未获取", ranked[0]["data_notes"])
        self.assertIn("LetPub新锐", ranked[0]["data_status"])

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

    def test_report_warns_when_candidate_recall_is_low_confidence(self):
        profile = {
            "categories": [{"category1": "环境科学与生态学", "category2": "水资源", "score": 3}],
            "matched_terms": ["hydrology"],
            "methods": ["machine learning"],
        }
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "High Impact Broad Methods",
                    "impact_factor": "12",
                    "partition": "1区",
                    "sci_type": "SCIE",
                    "field": "Computer Science; Artificial Intelligence",
                    "_sources": ["letpub", "openalex"],
                },
                {
                    "name": "General Environmental Reports",
                    "impact_factor": "6",
                    "partition": "2区",
                    "sci_type": "SCIE",
                    "field": "Environmental Sciences",
                    "_sources": ["letpub"],
                },
            ],
        )

        report = format_selection_report(profile, ranked)

        self.assertIn("候选召回置信度较低", report)
        self.assertIn("不要仅按 IF 或分区决策", report)

    def test_profile_separates_methods_from_topic_evidence(self):
        profile = infer_paper_profile(
            "Machine learning and GIS are used to map flash flood susceptibility "
            "from rainfall, terrain, and land-use data."
        )

        self.assertIn("machine learning", profile["methods"])
        self.assertIn("gis", profile["methods"])
        self.assertIn("flash flood", profile["topic_evidence"])
        self.assertNotEqual(profile["primary_signal"], "machine learning")

    def test_topic_evidence_can_outrank_broad_high_if_match(self):
        profile = infer_paper_profile(
            "Machine learning and GIS are used to map flash flood susceptibility "
            "from rainfall, terrain, and land-use data."
        )
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "High Impact AI Letters",
                    "impact_factor": "15",
                    "partition": "1区",
                    "sci_type": "SCIE",
                    "field": "Computer Science; Artificial Intelligence",
                    "_sources": ["letpub", "openalex"],
                },
                {
                    "name": "Natural Hazards and Earth System Sciences",
                    "impact_factor": "4.6",
                    "partition": "2区",
                    "sci_type": "SCIE",
                    "field": "Natural hazards; flash flood; rainfall; terrain",
                    "_sources": ["letpub", "openalex"],
                },
            ],
        )

        self.assertEqual(ranked[0]["name"], "Natural Hazards and Earth System Sciences")
        self.assertIn("细分主题", "；".join(ranked[0]["fit_reasons"]))

    def test_official_finder_checklist_is_manual_and_opt_in(self):
        checklist = build_finder_checklist(
            title="Status separation before estimating nitrate reference conditions",
            abstract="This study tested a geology-constrained hydrochemical framework.",
            keywords=["groundwater", "nitrate", "hydrochemistry"],
        )
        report = format_finder_checklist(checklist)

        self.assertIn("Elsevier Journal Finder", report)
        self.assertIn("Springer Nature Journal Finder", report)
        self.assertIn("groundwater; nitrate; hydrochemistry", report)
        self.assertIn("手动打开", report)
        self.assertIn("可选", report)
        self.assertNotIn("cookie", report.lower())
        self.assertNotIn("自动登录", report)
        self.assertNotIn("模拟登录", report)


if __name__ == "__main__":
    unittest.main()
