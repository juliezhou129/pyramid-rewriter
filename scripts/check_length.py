#!/usr/bin/env python3
"""Count a selected plain-text body and enforce inclusive character bounds."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import unicodedata


def check_length(text, minimum=None, maximum=None, exclude_punctuation=False):
    if minimum is not None and minimum < 0:
        raise ValueError("minimum must be nonnegative")
    if maximum is not None and maximum < 0:
        raise ValueError("maximum must be nonnegative")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("minimum must not exceed maximum")
    counted = "".join(
        char for char in text
        if not char.isspace()
        and not (exclude_punctuation and unicodedata.category(char).startswith("P"))
    )
    count = len(counted)
    missing = max(0, minimum - count) if minimum is not None else 0
    excess = max(0, count - maximum) if maximum is not None else 0
    return {
        "count": count,
        "minimum": minimum,
        "maximum": maximum,
        "within_range": not (missing or excess),
        "missing": missing,
        "excess": excess,
        "count_mode": (
            "non_whitespace_unicode_characters_excluding_punctuation"
            if exclude_punctuation else "non_whitespace_unicode_characters"
        ),
        "counted_text_sha256": hashlib.sha256(counted.encode("utf-8")).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="统计选定的纯正文；默认含标点和数字，不计空白。不会自动识别标题或编辑说明。"
    )
    parser.add_argument("file", nargs="?", default="-", help="UTF-8正文文件，或 - 从标准输入读取")
    parser.add_argument("--min", type=int, dest="minimum")
    parser.add_argument("--max", type=int, dest="maximum")
    parser.add_argument("--exclude-punctuation", action="store_true")
    parser.add_argument("--label", default="正文")
    args = parser.parse_args()
    try:
        # Validate bounds before reading stdin, so invalid commands fail promptly.
        check_length("", args.minimum, args.maximum, args.exclude_punctuation)
        text = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
        result = check_length(text, args.minimum, args.maximum, args.exclude_punctuation)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.error(str(exc))
    result["label"] = args.label
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["within_range"] else 1


if __name__ == "__main__":
    sys.exit(main())
