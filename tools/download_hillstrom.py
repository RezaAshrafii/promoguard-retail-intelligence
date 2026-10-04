"""Download the public Hillstrom challenge CSV without adding it to Git."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from promoguard.experiments.hillstrom import HILLSTROM_DOWNLOAD_URL


def download(output: Path, *, force: bool = False) -> dict[str, str | int]:
    """Fetch the publisher-linked CSV using an atomic local write."""
    output = output.resolve()
    if output.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing file: {output}; pass --force to replace it")
    output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    byte_count = 0
    request = Request(HILLSTROM_DOWNLOAD_URL, headers={"User-Agent": "PromoGuard public benchmark research"})
    temporary_path: Path | None = None
    try:
        with urlopen(request, timeout=60) as response:
            if response.status != 200:
                raise OSError(f"Publisher returned HTTP {response.status}")
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=f"{output.name}.", suffix=".part", dir=output.parent, delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                while chunk := response.read(1024 * 1024):
                    temporary.write(chunk)
                    digest.update(chunk)
                    byte_count += len(chunk)
        if byte_count == 0:
            raise OSError("Publisher returned an empty file")
        if output.exists() and not force:
            raise FileExistsError(f"Refusing to overwrite existing file: {output}")
        os.replace(temporary_path, output)
        return {"path": str(output), "bytes": byte_count, "sha256": digest.hexdigest()}
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/hillstrom/hillstrom-email-analytics-2008.csv"),
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing output file")
    arguments = parser.parse_args()
    import json

    print(json.dumps(download(arguments.output, force=arguments.force), indent=2))


if __name__ == "__main__":
    main()
