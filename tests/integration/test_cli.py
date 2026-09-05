from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

import promoguard.cli as cli_module


def run_cli(monkeypatch: pytest.MonkeyPatch, *arguments: str) -> None:
    monkeypatch.setattr(sys, "argv", ["promoguard", *arguments])
    cli_module.main()


def test_health_command_reports_a_clean_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run_cli(monkeypatch, "health")

    assert capsys.readouterr().out.strip() == "PromoGuard core is healthy"


def test_ingest_command_refuses_missing_required_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(SystemExit) as error:
        run_cli(monkeypatch, "ingest")

    assert error.value.code == 2


def test_validate_command_emits_machine_readable_quality_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "dunnhumby_transactions.csv"
    pd.read_csv(fixture).to_csv(tmp_path / "transactions.csv", index=False)

    run_cli(monkeypatch, "validate", "--input", str(tmp_path))

    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["rows"] == 2


def test_uplift_command_writes_exact_domain_payload(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.csv.gz"
    source.write_bytes(b"placeholder")
    output = tmp_path / "report"
    expected = {"benchmark": "test", "gate": {"promotion_allowed": False}}
    monkeypatch.setattr(cli_module, "evaluate_uplift_models", lambda *args, **kwargs: expected)

    run_cli(
        monkeypatch,
        "uplift-benchmark",
        "--input",
        str(source),
        "--output",
        str(output),
    )

    stored = json.loads((output / "criteo-uplift-model-ranking.json").read_text("utf-8"))
    assert stored == expected
    assert json.loads(capsys.readouterr().out) == expected
