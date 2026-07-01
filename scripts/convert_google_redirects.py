#!/usr/bin/env python3
"""Detect (and optionally fix) old Google redirect URLs
(http://www.google.com/url?q=...) in markdown files, replacing them with
their decoded target URL."""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from convert_raw_links import (
    FENCE_RE,
    INLINE_CODE_RE,
    TRAILING_PUNCTUATION,
    iter_markdown_files,
)

GOOGLE_REDIRECT_RE = re.compile(r"https?://(?:www\.)?google\.[^/\s]+/url\?[^\s\[\]<>`()]+")

_quiet = False


def log(message: str) -> None:
    if not _quiet:
        print(message)


@dataclass
class GoogleRedirect:
    line: int
    col: int
    original: str
    resolved: str


def _resolve(redirect_url: str) -> str | None:
    query = parse_qs(urlsplit(redirect_url).query)
    targets = query.get("q")
    if not targets:
        return None
    target = unquote(targets[0])
    if target.startswith("http://"):
        target = "https://" + target[len("http://"):]
    if not target.startswith("https://"):
        return None
    return target


def find_google_redirects(text: str) -> list[GoogleRedirect]:
    redirects = []
    in_code_block = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        code_spans = [m.span() for m in INLINE_CODE_RE.finditer(line)]
        for match in GOOGLE_REDIRECT_RE.finditer(line):
            if any(match.start() >= s and match.end() <= e for s, e in code_spans):
                continue
            original = match.group().rstrip(TRAILING_PUNCTUATION)
            resolved = _resolve(original)
            if resolved is None:
                continue
            redirects.append(
                GoogleRedirect(line=line_number, col=match.start(), original=original, resolved=resolved)
            )
    return redirects


def fix_text(text: str) -> str:
    lines = text.splitlines(keepends=True)
    redirects_by_line: dict[int, list[GoogleRedirect]] = {}
    for redirect in find_google_redirects(text):
        redirects_by_line.setdefault(redirect.line, []).append(redirect)

    fixed_lines = []
    for line_number, line in enumerate(lines, start=1):
        line_redirects = redirects_by_line.get(line_number)
        if not line_redirects:
            fixed_lines.append(line)
            continue
        for redirect in sorted(line_redirects, key=lambda r: r.col, reverse=True):
            end = redirect.col + len(redirect.original)
            line = line[: redirect.col] + redirect.resolved + line[end:]
        fixed_lines.append(line)
    return "".join(fixed_lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="markdown file or directory to scan")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite files in place, replacing Google redirect URLs with their target",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress output; exit code still reflects whether redirects were found",
    )
    args = parser.parse_args()

    global _quiet
    _quiet = args.quiet

    if not args.path.exists():
        print(f"error: path not found: {args.path}", file=sys.stderr)
        return 2

    found_any = False
    for md_file in iter_markdown_files(args.path):
        text = md_file.read_text(encoding="utf-8")
        redirects = find_google_redirects(text)
        if not redirects:
            continue
        found_any = True
        for redirect in redirects:
            log(f'"{md_file}:{redirect.line}" : {redirect.original} -> {redirect.resolved}')
        if args.fix:
            md_file.write_text(fix_text(text), encoding="utf-8")
            log(f"fixed {len(redirects)} google redirect(s) in {md_file}")

    if args.fix:
        return 0
    return 1 if found_any else 0


if __name__ == "__main__":
    sys.exit(main())
