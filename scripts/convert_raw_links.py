#!/usr/bin/env python3
"""Detect (and optionally fix) raw https:// URLs in markdown files that
are not wrapped in markdown link syntax."""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

RAW_URL_RE = re.compile(r"https?://[^\s\[\]<>`()]+")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]*\)")
AUTOLINK_RE = re.compile(r"<https?://[^>]+>")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
TRAILING_PUNCTUATION = ".,;:!?)]}'\""


_quiet = False


def log(message: str) -> None:
    if not _quiet:
        print(message)


@dataclass
class RawLink:
    line: int
    col: int
    url: str


def _protected_spans(line: str) -> list[tuple[int, int]]:
    spans = []
    for pattern in (INLINE_CODE_RE, MARKDOWN_LINK_RE, AUTOLINK_RE):
        spans.extend(match.span() for match in pattern.finditer(line))
    return spans


def _is_protected(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start >= s and end <= e for s, e in spans)


def _strip_trailing_punctuation(url: str) -> str:
    return url.rstrip(TRAILING_PUNCTUATION)


def find_raw_links(text: str) -> list[RawLink]:
    links = []
    in_code_block = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        spans = _protected_spans(line)
        for match in RAW_URL_RE.finditer(line):
            if _is_protected(match.start(), match.end(), spans):
                continue
            url = _strip_trailing_punctuation(match.group())
            if not url:
                continue
            links.append(RawLink(line=line_number, col=match.start(), url=url))
    return links


def fix_text(text: str) -> str:
    lines = text.splitlines(keepends=True)
    links_by_line: dict[int, list[RawLink]] = {}
    for link in find_raw_links(text):
        links_by_line.setdefault(link.line, []).append(link)

    fixed_lines = []
    for line_number, line in enumerate(lines, start=1):
        line_links = links_by_line.get(line_number)
        if not line_links:
            fixed_lines.append(line)
            continue
        for link in sorted(line_links, key=lambda l: l.col, reverse=True):
            end = link.col + len(link.url)
            replacement = f"[{link.url}]({link.url})"
            line = line[: link.col] + replacement + line[end:]
        fixed_lines.append(line)
    return "".join(fixed_lines)


def iter_markdown_files(path: Path) -> Iterator[Path]:
    if path.is_file():
        yield path
    else:
        yield from sorted(path.rglob("*.md"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="markdown file or directory to scan")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite files in place, wrapping raw URLs in markdown link syntax",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress output; exit code still reflects whether raw links were found",
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
        links = find_raw_links(text)
        if not links:
            continue
        found_any = True
        for link in links:
            log(f'"{md_file}:{link.line}" : {link.url}')
        if args.fix:
            md_file.write_text(fix_text(text), encoding="utf-8")
            log(f"fixed {len(links)} raw link(s) in {md_file}")

    if args.fix:
        return 0
    return 1 if found_any else 0


if __name__ == "__main__":
    sys.exit(main())
