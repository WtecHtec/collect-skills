#!/usr/bin/env python3
"""Check a Chinese TTS script for length and unstable-reading risks."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ALLOWED_PUNCTUATION = {"，", "。", "？", "！"}
SENTENCE_TERMINATORS = {"。", "？", "！"}
FORBIDDEN_ASCII_PUNCTUATION = set(":;\"'()[]{}<>/\\|@#$%^&*+=~`_-.")
FORBIDDEN_CJK_PUNCTUATION = set("：；“”‘’（）【】《》〈〉——…、·￥﹏～")
MARKDOWN_LINE_RE = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|>\s|```|\|)")
UPPERCASE_RUN_RE = re.compile(r"[A-Z]{2,}")
LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")
ARABIC_DIGIT_RE = re.compile(r"[0-9]")
URL_RE = re.compile(r"(?:https?://|www\.|\b\w+[.]\w{2,}\b)", re.IGNORECASE)
SOURCE_CONTAINER_RE = re.compile(
    r"(?:这篇文章|文章(?:里|中|还)?(?:讲了|提到|写道|认为)|"
    r"原文(?:里|中)?(?:提到|写道|认为)|"
    r"素材(?:里|中)?(?:提到|写道|说)|"
    r"作者(?:接着|还)?(?:提到|写道|表示|认为)|"
    r"从这段内容(?:中)?可以看出)"
)


def line_column(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    last_newline = text.rfind("\n", 0, index)
    column = index - last_newline
    return line, column


def add_issue(
    issues: list[tuple[str, int, int, str]],
    level: str,
    text: str,
    index: int,
    message: str,
) -> None:
    line, column = line_column(text, index)
    issues.append((level, line, column, message))


def character_count(text: str) -> int:
    """Count every code point except line breaks, including spaces and punctuation."""
    return sum(char not in {"\r", "\n"} for char in text)


def first_sentence(text: str) -> str:
    """Return the first spoken sentence, including its terminal if present."""
    stripped = text.lstrip()
    for index, char in enumerate(stripped):
        if char in SENTENCE_TERMINATORS:
            return stripped[: index + 1]
    return stripped


def spoken_unit_count(text: str) -> int:
    """Count characters likely to be spoken, excluding whitespace and punctuation."""
    return sum(
        not char.isspace() and char not in ALLOWED_PUNCTUATION
        for char in text
    )


def check_text(
    text: str,
    max_chars: int = 1200,
    max_hook_units: int = 18,
) -> list[tuple[str, int, int, str]]:
    issues: list[tuple[str, int, int, str]] = []

    count = character_count(text)
    if count > max_chars:
        issues.append(
            (
                "ERROR",
                1,
                1,
                f"正文共 {count} 字符，超过硬上限 {max_chars}",
            )
        )

    hook = first_sentence(text)
    hook_units = spoken_unit_count(hook)
    if max_hook_units and hook_units > max_hook_units:
        issues.append(
            (
                "WARNING",
                1,
                1,
                f"首句共 {hook_units} 个可朗读单位，超过前三秒钩子建议上限 {max_hook_units}",
            )
        )
    if hook and not any(char in SENTENCE_TERMINATORS for char in hook):
        issues.append(("WARNING", 1, 1, "首句缺少句末标点，无法可靠判断前三秒钩子"))

    for line_number, line in enumerate(text.splitlines(), start=1):
        if MARKDOWN_LINE_RE.search(line):
            issues.append(("ERROR", line_number, 1, "发现 Markdown 或列表格式"))

    for index, char in enumerate(text):
        if char in FORBIDDEN_ASCII_PUNCTUATION or char in FORBIDDEN_CJK_PUNCTUATION:
            add_issue(issues, "ERROR", text, index, f"发现高风险标点或符号 {char!r}")

    for match in UPPERCASE_RUN_RE.finditer(text):
        add_issue(
            issues,
            "ERROR",
            text,
            match.start(),
            f"连续大写字母 {match.group()!r} 应拆分为逐字母读法",
        )

    for match in ARABIC_DIGIT_RE.finditer(text):
        add_issue(
            issues,
            "WARNING",
            text,
            match.start(),
            f"阿拉伯数字 {match.group()!r} 需要确认朗读方式",
        )

    uppercase_spans = {match.span() for match in UPPERCASE_RUN_RE.finditer(text)}
    for match in LATIN_WORD_RE.finditer(text):
        if match.span() in uppercase_spans:
            continue
        add_issue(
            issues,
            "WARNING",
            text,
            match.start(),
            f"英文组合 {match.group()!r} 需要确认 TTS 发音",
        )

    for match in URL_RE.finditer(text):
        add_issue(
            issues,
            "ERROR",
            text,
            match.start(),
            f"网址或域名 {match.group()!r} 不应直接进入默认口播正文",
        )

    for match in SOURCE_CONTAINER_RE.finditer(text):
        add_issue(
            issues,
            "ERROR",
            text,
            match.start(),
            f"发现来源容器表达 {match.group()!r}，应直接讲述内容",
        )

    return sorted(issues, key=lambda item: (item[1], item[2], item[0]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="UTF-8 plain-text TTS script")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as validation failures",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1200,
        help="Hard character limit, excluding line breaks (default: 1200)",
    )
    parser.add_argument(
        "--max-hook-units",
        type=int,
        default=18,
        help="Recommended maximum spoken units in the first sentence (default: 18; 0 disables)",
    )
    args = parser.parse_args()

    if args.max_chars <= 0:
        parser.error("--max-chars must be positive")
    if args.max_hook_units < 0:
        parser.error("--max-hook-units must be zero or positive")

    try:
        text = args.path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {args.path}: {exc}", file=sys.stderr)
        return 2

    count = character_count(text)
    issues = check_text(text, args.max_chars, args.max_hook_units)
    if not issues:
        print(
            "OK: no obvious TTS text risks found "
            f"({count}/{args.max_chars} max)"
        )
        return 0

    for level, line, column, message in issues:
        print(f"{level} {line}:{column} {message}")

    errors = sum(level == "ERROR" for level, *_ in issues)
    warnings = sum(level == "WARNING" for level, *_ in issues)
    print(
        f"Summary: {errors} error(s), {warnings} warning(s), "
        f"{count} character(s), {args.max_chars} max"
    )

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
