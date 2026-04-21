from tax_rag import DEFAULT_CONFIG, __version__


def test_package_imports() -> None:
    assert __version__ == "0.1.0"


def test_default_config_values() -> None:
    assert DEFAULT_CONFIG.security.enforcement_stage == "pre_retrieval"
    assert DEFAULT_CONFIG.retrieval.fusion_strategy == "rrf"
    assert "faithfulness" in DEFAULT_CONFIG.evaluation.metrics
