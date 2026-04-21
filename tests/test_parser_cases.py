from pathlib import Path

from tax_rag.ingestion.parser_cases import parse_case_file
from tax_rag.schemas import SourceType


HR_CASE_PATH = Path("data/raw/cases/ecli_nl_hr_2025_99.xml")
GHDHA_CASE_PATH = Path("data/raw/cases/ecli_nl_ghdha_2023_2457.xml")


def test_parse_case_file_extracts_core_metadata() -> None:
    document = parse_case_file(HR_CASE_PATH)

    assert document.source_type is SourceType.CASE_LAW
    assert document.ecli == "ECLI:NL:HR:2025:99"
    assert document.court == "Hoge Raad"
    assert document.decision_date == "2025-01-17"


def test_parse_case_file_includes_summary_and_sections_in_text() -> None:
    document = parse_case_file(GHDHA_CASE_PATH)

    assert "30%-regeling" in document.text
    assert "Procesverloop" in document.text
    assert "Feiten" in document.text
    assert document.source_path == str(GHDHA_CASE_PATH)
