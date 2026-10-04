"""Fetch and verify the public Complete Journey research archive in byte ranges."""

from __future__ import annotations

import hashlib
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

URL = (
    "https://github.com/bltap-plmarket/dunnhumby-complete-journey/releases/download/"
    "v1.0-data/dunnhumby-complete-journey-data.zip"
)
SIZE = 135_859_064
SHA256 = "324288a8811c4ed86e85415fdee36f3692582e2cc9dd87866c0e333df237f782"
CHUNK_SIZE = 8 * 1024 * 1024
DESTINATION = Path(__file__).resolve().parents[1] / "data/raw/complete-journey"


def fetch_chunk(index: int, start: int, end: int) -> tuple[int, Path]:
    path = DESTINATION / f"archive.range-{index:02}.part"
    expected_size = end - start + 1
    if path.is_file() and path.stat().st_size == expected_size:
        return index, path
    request = urllib.request.Request(URL, headers={"Range": f"bytes={start}-{end}"})
    temporary = path.with_suffix(".download")
    with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as output:
        if response.status != 206:
            raise RuntimeError(f"Server ignored range request for chunk {index}: {response.status}")
        actual_range = response.headers.get("Content-Range", "")
        if not actual_range.startswith(f"bytes {start}-{end}/"):
            raise RuntimeError(f"Unexpected Content-Range for chunk {index}: {actual_range}")
        while block := response.read(1024 * 1024):
            output.write(block)
    if temporary.stat().st_size != expected_size:
        raise RuntimeError(f"Incomplete download chunk {index}")
    os.replace(temporary, path)
    return index, path


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    chunks = [
        (i, start, min(start + CHUNK_SIZE - 1, SIZE - 1))
        for i, start in enumerate(range(0, SIZE, CHUNK_SIZE))
    ]
    files: dict[int, Path] = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(fetch_chunk, *chunk) for chunk in chunks]
        for future in as_completed(futures):
            index, path = future.result()
            files[index] = path
            print(f"Downloaded verified range {index + 1}/{len(chunks)}", flush=True)

    temporary = DESTINATION / "archive.verified.tmp"
    digest = hashlib.sha256()
    size = 0
    with temporary.open("wb") as output:
        for index in range(len(chunks)):
            with files[index].open("rb") as part:
                while block := part.read(4 * 1024 * 1024):
                    output.write(block)
                    digest.update(block)
                    size += len(block)
    if size != SIZE or digest.hexdigest() != SHA256:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Archive integrity check failed: bytes={size}, sha256={digest.hexdigest()}")

    final_path = DESTINATION / "dunnhumby-complete-journey-data.zip"
    os.replace(temporary, final_path)
    for path in files.values():
        path.unlink(missing_ok=True)
    print(f"Verified archive: {final_path} ({size} bytes, sha256={digest.hexdigest()})")


if __name__ == "__main__":
    main()
