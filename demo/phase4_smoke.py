"""Run the Phase 4 API path against the real canonical weekly panel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from apps.api.main import app

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPOSITORY_ROOT / "data" / "processed" / "breakfast-at-the-frat"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "reports" / "phase-04" / "demo-smoke.json"


def _require_success(response, step: str) -> dict[str, Any]:
    if not response.is_success:
        raise RuntimeError(f"{step} failed ({response.status_code}): {response.text}")
    return response.json()


def run_demo(input_path: Path) -> dict[str, Any]:
    """Exercise health, validation, event discovery, and audit HTTP boundaries."""
    client = TestClient(app)
    try:
        display_input = input_path.resolve().relative_to(REPOSITORY_ROOT).as_posix()
    except ValueError:
        display_input = str(input_path)
    health = _require_success(client.get("/health"), "health")
    request_path = {"input_path": str(input_path)}
    quality = _require_success(
        client.post("/v1/panels/validate", json=request_path), "panel validation"
    )
    promotions = _require_success(
        client.post("/v1/promotions", json={**request_path, "limit": 5}),
        "promotion discovery",
    )
    audit = _require_success(client.post("/v1/audits", json=request_path), "promotion audit")
    return {
        "status": "passed",
        "input_path": display_input,
        "health": health,
        "quality": {
            "valid": quality["valid"],
            "rows": quality["rows"],
            "series": quality["series"],
            "promotion_rows": quality["promotion_rows"],
            "date_min": quality["date_min"],
            "date_max": quality["date_max"],
        },
        "promotion_discovery": {
            "count": promotions["count"],
            "returned": promotions["returned"],
            "first_audit_id": promotions["events"][0]["audit_id"],
        },
        "audit": {
            "audit_id": audit["audit_id"],
            "observed_units": audit["observed_units"],
            "baseline_units": audit["baseline_units"],
            "incremental_units": audit["incremental_units"],
            "decision": audit["decision"],
            "warning_codes": [warning["code"] for warning in audit["warnings"]],
            "claim_language": audit["claim_language"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run_demo(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Phase 4 smoke evidence written to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
