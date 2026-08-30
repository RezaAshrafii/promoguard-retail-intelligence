"""Small command-line entry point for the initial scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from promoguard.data.dunnhumby import build_panel, load_dataset, validate_transactions


def main() -> None:
    parser = argparse.ArgumentParser(prog="promoguard")
    parser.add_argument("command", choices=["health", "ingest", "validate"], nargs="?", default="health")
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


if __name__ == "__main__":
    main()
