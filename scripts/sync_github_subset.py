#!/usr/bin/env python3
"""Sync a subset of a GitHub repository via the GitHub API.

This helper is designed for environments where full `git clone` is unstable.
It downloads only the requested files/directories from a public repository and
records the upstream commit for reproducibility.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import pathlib
import shutil
import sys
import urllib.error
import urllib.request


API_ROOT = "https://api.github.com/repos"
RAW_ROOT = "https://raw.githubusercontent.com"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Dprompt-sync-github-subset",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def download_file(url: str, dest: pathlib.Path) -> None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Dprompt-sync-github-subset"},
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as fh:
        shutil.copyfileobj(resp, fh)


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def should_include(path: str, includes: list[str], excludes: list[str]) -> bool:
    included = False
    for prefix in includes:
        if path == prefix or path.startswith(prefix.rstrip("/") + "/"):
            included = True
            break
    if not included:
        return False
    if excludes and matches_any(path, excludes):
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--ref", default="main", help="branch, tag, or commit")
    parser.add_argument("--output", required=True, help="target directory")
    parser.add_argument(
        "--include",
        action="append",
        required=True,
        help="path prefix to include; repeatable",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="glob pattern to exclude; repeatable",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="remove the output directory before syncing",
    )
    args = parser.parse_args()

    output_dir = pathlib.Path(args.output).resolve()
    if args.clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    commit_meta = fetch_json(f"{API_ROOT}/{args.repo}/commits/{args.ref}")
    commit_sha = commit_meta["sha"]
    tree = fetch_json(f"{API_ROOT}/{args.repo}/git/trees/{commit_sha}?recursive=1")

    files = []
    for item in tree.get("tree", []):
        if item.get("type") != "blob":
            continue
        path = item["path"]
        if should_include(path, args.include, args.exclude):
            files.append(path)

    if not files:
        print("No files matched the requested prefixes.", file=sys.stderr)
        return 1

    for rel_path in files:
        dest = output_dir / rel_path
        raw_url = f"{RAW_ROOT}/{args.repo}/{commit_sha}/{rel_path}"
        try:
            download_file(raw_url, dest)
        except urllib.error.HTTPError as exc:
            print(f"Failed to download {rel_path}: {exc}", file=sys.stderr)
            return 1

    manifest = {
        "repo": args.repo,
        "ref": args.ref,
        "commit": commit_sha,
        "include": args.include,
        "exclude": args.exclude,
        "file_count": len(files),
    }
    with (output_dir / ".sync_manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=True, indent=2)
        fh.write("\n")

    print(
        json.dumps(
            {
                "output": str(output_dir),
                "commit": commit_sha,
                "file_count": len(files),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
