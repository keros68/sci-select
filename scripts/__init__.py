"""sci-aiselect package."""

from .select_journals import (
    infer_paper_profile,
    select_journals,
    rank_metric_records,
    format_selection_report,
    format_selection_matrix,
    assign_submission_bands,
)

__all__ = [
    "infer_paper_profile",
    "select_journals",
    "rank_metric_records",
    "format_selection_report",
    "format_selection_matrix",
    "assign_submission_bands",
]
