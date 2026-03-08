#!/usr/bin/env python3
"""
add_zhuyin_ivs.py: Add IVS (Ideographic Variation Selector) markers to EPUB
for ToneOZ zhuyin font polyphone support.

Uses pypinyin to detect correct pronunciation in context, then inserts
invisible Unicode variation selectors so the ToneOZ font displays the
right zhuyin annotation for each character.

Dependencies:
    pip install pypinyin

Usage:
    python3 add_zhuyin_ivs.py input.epub [-o output.epub]
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

try:
    from pypinyin import pinyin, Style
except ImportError:
    print("Error: pypinyin is required. Install with: pip install pypinyin", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Load phonic table (char → [zhuyin1, zhuyin2, ...])
# ---------------------------------------------------------------------------

def load_phonic_table(table_path):
    """Load ToneOZ phonic_table_Z.txt mapping."""
    char_readings = {}
    with open(table_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            char = parts[0]
            readings = [p.strip() for p in parts[1:] if p.strip()]
            if readings:
                char_readings[char] = readings
    return char_readings


def normalize_zhuyin(z):
    """Normalize zhuyin format for comparison.

    pypinyin outputs neutral tone as suffix: ㄌㄜ˙
    ToneOZ table uses prefix: ˙ㄌㄜ
    Normalize both to the same form.
    """
    z = z.strip()
    # pypinyin suffix neutral tone → prefix
    if z.endswith("˙"):
        z = "˙" + z[:-1]
    return z


def find_reading_index(char, zhuyin, phonic_table):
    """Find which reading index (ss00, ss01, ...) matches the given zhuyin.

    Returns the IVS variation selector codepoint, or None if no match / default.
    """
    if char not in phonic_table:
        return None

    readings = phonic_table[char]
    if len(readings) <= 1:
        return None  # Only one reading, no IVS needed

    normalized = normalize_zhuyin(zhuyin)

    for i, reading in enumerate(readings):
        if normalize_zhuyin(reading) == normalized:
            if i == 0:
                return None  # Default reading, no IVS needed
            return 0xE01E0 + i  # U+E01E0 = ss00, U+E01E1 = ss01, etc.

    return None  # No match found, use default


# ---------------------------------------------------------------------------
# CJK character detection
# ---------------------------------------------------------------------------

_CJK_RE = re.compile(
    r"[\u4e00-\u9fff"          # CJK Unified Ideographs
    r"\u3400-\u4dbf"           # CJK Extension A
    r"\U00020000-\U0002a6df"   # CJK Extension B
    r"\uf900-\ufaff]"          # CJK Compatibility Ideographs
)


def is_cjk(char):
    return bool(_CJK_RE.match(char))


# ---------------------------------------------------------------------------
# Process text with IVS markers
# ---------------------------------------------------------------------------

def _t2s(text):
    """Convert Traditional Chinese to Simplified for better pypinyin phrase matching."""
    try:
        proc = subprocess.run(
            ["opencc", "-c", "tw2sp"],
            input=text,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return proc.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return text  # Fallback: use original


def add_ivs_to_text(text, phonic_table, stats):
    """Add IVS markers to CJK characters in text based on pypinyin analysis.

    Converts to Simplified Chinese first for better pypinyin phrase matching,
    then maps results back to the original Traditional characters.
    Only processes text content, skips HTML tags.
    """
    # Split text into tag and non-tag segments
    segments = re.split(r"(<[^>]+>)", text)
    result = []

    for segment in segments:
        if segment.startswith("<"):
            result.append(segment)
            continue

        # Process text segment
        chars = list(segment)
        if not any(is_cjk(c) for c in chars):
            result.append(segment)
            continue

        # Convert to simplified for better pypinyin phrase matching
        simplified = _t2s(segment)

        # Get pinyin for simplified text (context-aware)
        try:
            readings = pinyin(simplified, style=Style.BOPOMOFO, errors="default")
        except Exception:
            result.append(segment)
            continue

        # Apply IVS to original traditional characters
        new_segment = []
        reading_idx = 0
        for char in chars:
            new_segment.append(char)
            if is_cjk(char) and reading_idx < len(readings):
                zhuyin = readings[reading_idx][0]
                stats["total_cjk"] += 1

                vs = find_reading_index(char, zhuyin, phonic_table)
                if vs is not None:
                    new_segment.append(chr(vs))
                    stats["ivs_inserted"] += 1

                reading_idx += 1
            elif is_cjk(char):
                reading_idx += 1

        result.append("".join(new_segment))

    return "".join(result)


# ---------------------------------------------------------------------------
# EPUB processing
# ---------------------------------------------------------------------------

def process_epub(input_path, output_path, phonic_table):
    """Process all XHTML files in EPUB, adding IVS markers."""
    tmpdir = tempfile.mkdtemp()
    stats = {"total_cjk": 0, "ivs_inserted": 0, "files_processed": 0}

    try:
        with zipfile.ZipFile(input_path, "r") as zin:
            zin.extractall(tmpdir)

        # Process all XHTML/HTML files
        for root, _dirs, files in os.walk(tmpdir):
            for f in files:
                if not (f.endswith(".xhtml") or f.endswith(".html")):
                    continue

                fpath = os.path.join(root, f)
                html = open(fpath, "r", encoding="utf-8").read()

                # Only process body content
                body_match = re.search(r"(<body[^>]*>)(.*?)(</body>)", html, re.DOTALL)
                if not body_match:
                    continue

                before = html[: body_match.start(2)]
                body = body_match.group(2)
                after = html[body_match.end(2):]

                new_body = add_ivs_to_text(body, phonic_table, stats)

                if new_body != body:
                    html = before + new_body + after
                    open(fpath, "w", encoding="utf-8").write(html)
                    stats["files_processed"] += 1

                # Progress
                if stats["files_processed"] % 100 == 0 and stats["files_processed"] > 0:
                    print(f"  Processed {stats['files_processed']} files, "
                          f"{stats['total_cjk']} chars, "
                          f"{stats['ivs_inserted']} IVS inserted...")

        # Repack EPUB
        with zipfile.ZipFile(output_path, "w") as zout:
            mimetype = os.path.join(tmpdir, "mimetype")
            if os.path.exists(mimetype):
                zout.write(mimetype, "mimetype", compress_type=zipfile.ZIP_STORED)
            for root, _dirs, files in os.walk(tmpdir):
                for f in files:
                    full = os.path.join(root, f)
                    arcname = os.path.relpath(full, tmpdir)
                    if arcname == "mimetype":
                        continue
                    zout.write(full, arcname, compress_type=zipfile.ZIP_DEFLATED)
    finally:
        shutil.rmtree(tmpdir)

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Add IVS markers to EPUB for ToneOZ zhuyin font polyphone support"
    )
    p.add_argument("input", help="Input EPUB file")
    p.add_argument("-o", "--output", help="Output EPUB path (default: <input>_zhuyin.epub)")
    p.add_argument(
        "--phonic-table",
        default=os.path.join(os.path.dirname(__file__), "fonts", "phonic_table_Z.txt"),
        help="Path to phonic_table_Z.txt",
    )
    args = p.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    table_path = args.phonic_table
    if not os.path.isfile(table_path):
        print(f"Error: phonic table not found: {table_path}", file=sys.stderr)
        sys.exit(1)

    output = args.output
    if not output:
        base, ext = os.path.splitext(args.input)
        output = base + "_zhuyin" + ext

    print("Loading phonic table...")
    phonic_table = load_phonic_table(table_path)
    print(f"  {len(phonic_table)} characters, "
          f"{sum(1 for r in phonic_table.values() if len(r) > 1)} polyphones")

    print(f"Processing {args.input}...")
    stats = process_epub(args.input, output, phonic_table)

    print(f"\nDone! Output: {output}")
    print(f"  Files processed: {stats['files_processed']}")
    print(f"  CJK characters: {stats['total_cjk']}")
    print(f"  IVS markers inserted: {stats['ivs_inserted']}")
    print(f"\nUse with ToneOZ-Zhuyin-Kai-Traditional.ttf font on Kindle")


if __name__ == "__main__":
    main()
