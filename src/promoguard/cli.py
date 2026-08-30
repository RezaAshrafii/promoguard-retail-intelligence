"""Small command-line entry point for the initial scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from promoguard.data.dunnhumby import build_panel, load_dataset, validate_transactions
from promoguard.forecasting.evaluation import evaluate_backtest


def main() -> None:
    parser = argparse.ArgumentParser(prog="promoguard")
    parser.add_argument(
        "command",
        choices=["health", "ingest", "validate", "forecast-evaluate"],
        nargs="?",
        default="health",
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
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


if __name__ == "__main__":
    main()
