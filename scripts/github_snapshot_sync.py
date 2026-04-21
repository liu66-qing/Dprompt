#!/usr/bin/env python3
"""Download selected paths from a GitHub repo without cloning the full repository.

This is a fallback for unstable long-lived git/codeload connections. It walks the
remote tree once via the GitHub API, then downloads only the requested files from
raw.githubusercontent.com with retries.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


API_TREE_URL = "https://api.github.com/repos/{repo}/git/trees/{ref}?recursive=1"
RAW_URL = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
DEFAULT_HEADERS = {
    "User-Agent": "github-snapshot-sync/1.0",
    "Accept": "application/vnd.github+json",
}


def build_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers=DEFAULT_HEADERS)


def fetch_json(url: str, retries: int = 5, timeout: int = 60) -> dict:
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(build_request(url), timeout=timeout) as response:
                return json.load(response)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == retries:
                break
            time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"Failed to fetch JSON from {url}: {last_error}") from last_error


def normalize_prefix(prefix: str) -> str:
    return prefix.strip("/").strip()


def should_include(path: str, includes: list[str], excludes: list[str]) -> bool:
    normalized = path.strip("/")
    if includes:
        included = any(
            normalized == prefix or normalized.startswith(prefix + "/") for prefix in includes
        )
        if not included:
            return False
    if excludes:
        blocked = any(
            normalized == prefix or normalized.startswith(prefix + "/") for prefix in excludes
        )
        if blocked:
            return False
    return True


def ensure_parent(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def download_file(
    repo: str,
    ref: str,
    relpath: str,
    dest_root: pathlib.Path,
    expected_size: int | None,
    retries: int,
) -> tuple[str, str]:
    dest_path = dest_root / relpath
    ensure_parent(dest_path)

    if dest_path.exists() and expected_size is not None and dest_path.stat().st_size == expected_size:
        return relpath, "cached"

    encoded_path = urllib.parse.quote(relpath, safe="/")
    url = RAW_URL.format(repo=repo, ref=ref, path=encoded_path)
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(build_request(url), timeout=120) as response:
                data = response.read()
            if expected_size is not None and len(data) != expected_size:
                raise RuntimeError(
                    f"Size mismatch for {relpath}: got {len(data)}, expected {expected_size}"
                )
            tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
            with open(tmp_path, "wb") as handle:
                handle.write(data)
            os.replace(tmp_path, dest_path)
            return relpath, "downloaded"
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == retries:
                break
            time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"Failed to download {relpath}: {last_error}") from last_error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--ref", default="main")
    parser.add_argument("--dest", required=True)
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Path prefix to include. Repeatable. Empty means everything.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Path prefix to exclude. Repeatable.",
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--metadata-name", default=".github_snapshot_meta.json")
    args = parser.parse_args()

    includes = [normalize_prefix(item) for item in args.include if normalize_prefix(item)]
    excludes = [normalize_prefix(item) for item in args.exclude if normalize_prefix(item)]
    dest_root = pathlib.Path(args.dest).resolve()
    dest_root.mkdir(parents=True, exist_ok=True)

    tree_url = API_TREE_URL.format(repo=args.repo, ref=args.ref)
    tree = fetch_json(tree_url)
    blobs = []
    for entry in tree.get("tree", []):
        if entry.get("type") != "blob":
            continue
        path = entry["path"]
        if should_include(path, includes, excludes):
            blobs.append((path, entry.get("size")))

    if not blobs:
        print("No files matched include/exclude filters.", file=sys.stderr)
        return 1

    downloaded = 0
    cached = 0
    failures = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {
            executor.submit(
                download_file,
                args.repo,
                args.ref,
                path,
                dest_root,
                size,
                args.retries,
            ): path
            for path, size in blobs
        }
        for idx, future in enumerate(concurrent.futures.as_completed(future_map), start=1):
            path = future_map[future]
            try:
                _, status = future.result()
                if status == "cached":
                    cached += 1
                else:
                    downloaded += 1
                if idx % 20 == 0 or idx == len(blobs):
                    print(
                        f"[{idx}/{len(blobs)}] downloaded={downloaded} cached={cached} failures={len(failures)}"
                    )
            except Exception as exc:  # noqa: BLE001
                failures.append({"path": path, "error": str(exc)})
                print(f"[error] {path}: {exc}", file=sys.stderr)

    metadata = {
        "repo": args.repo,
        "ref": args.ref,
        "include": includes,
        "exclude": excludes,
        "file_count": len(blobs),
        "downloaded": downloaded,
        "cached": cached,
        "failures": failures,
        "generated_at_epoch": int(time.time()),
    }
    with open(dest_root / args.metadata_name, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    if failures:
        print(f"Completed with {len(failures)} failures.", file=sys.stderr)
        return 2

    print(f"Completed successfully: {downloaded} downloaded, {cached} cached.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
