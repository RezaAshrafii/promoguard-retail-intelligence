"""Small command-line entry point for the initial scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from promoguard.data.dunnhumby import build_panel, load_dataset, validate_transactions
from promoguard.forecasting.evaluation import evaluate_backtest
from promoguard.insights.promotion_audit import (
    audit_promotion_event,
    select_representative_event,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="promoguard")
    parser.add_argument(
        "command",
        choices=["health", "ingest", "validate", "forecast-evaluate", "promotion-audit"],
        nargs="?",
        default="health",
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--store-id")
    parser.add_argument("--upc")
    parser.add_argument("--start-date")
    parser.add_argument("--unit-margin", type=float)
    args = parser.parse_args()
    if args.command == "health":
        print("PromoGuard scaffold is healthy")
    elif args.command == "ingest":
        if args.input is None or args.output is None:
            parser.error("ingest requires --input and --output")
        result = build_panel(args.input, args.output)
        print(json.dumps(result, indent=2, default=str))
    elif args.command == "validate":
        if args.input is None:
            parser.error("validate requires --input")
        frames = load_dataset(args.input)
        print(json.dumps(validate_transactions(frames["transactions"]), indent=2, default=str))
    elif args.command == "forecast-evaluate":
        if args.input is None or args.output is None:
            parser.error("forecast-evaluate requires --input and --output")
        panel_path = args.input / "weekly_panel.csv" if args.input.is_dir() else args.input
        if not panel_path.exists():
            parser.error(f"weekly panel not found: {panel_path}")
        panel = pd.read_csv(panel_path, parse_dates=["week_end_date"])
        result = evaluate_backtest(panel)
        args.output.mkdir(parents=True, exist_ok=True)
        compact_result = {
            key: value
            for key, value in result.items()
            if key not in {"segment_metrics", "table_rows"}
        }
        (args.output / "forecast-evaluation.json").write_text(
            json.dumps(compact_result, indent=2, default=str), encoding="utf-8"
        )
        pd.DataFrame(result["table_rows"]).to_csv(
            args.output / "forecast-evaluation.csv", index=False
        )
        segment_rows = [
            row
            for rows in result["segment_metrics"].values()
            for row in rows
        ]
        pd.DataFrame(segment_rows).to_csv(
            args.output / "forecast-segment-metrics.csv", index=False
        )
        print(json.dumps(compact_result, indent=2, default=str))
    elif args.command == "promotion-audit":
        if args.input is None or args.output is None:
            parser.error("promotion-audit requires --input and --output")
        panel_path = args.input / "weekly_panel.csv" if args.input.is_dir() else args.input
        if not panel_path.exists():
            parser.error(f"weekly panel not found: {panel_path}")
        supplied_keys = [args.store_id, args.upc, args.start_date]
        if any(supplied_keys) and not all(supplied_keys):
            parser.error("provide --store-id, --upc, and --start-date together, or omit all three")
        panel = pd.read_csv(panel_path, parse_dates=["week_end_date"])
        selection = (
            {
                "store_id": args.store_id,
                "upc": args.upc,
                "start_date": args.start_date,
            }
            if all(supplied_keys)
            else select_representative_event(panel)
        )
        result = audit_promotion_event(
            panel,
            store_id=str(selection["store_id"]),
            upc=str(selection["upc"]),
            start_date=selection["start_date"],
            unit_margin=args.unit_margin,
        )
        payload = result.model_dump(mode="json")
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "promotion-audit.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        window_rows = [
            {"window": name, **getattr(result, f"{name}_window").model_dump()}
            for name in ("pre", "during", "post")
        ]
        pd.DataFrame(window_rows).to_csv(args.output / "promotion-audit-windows.csv", index=False)
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
