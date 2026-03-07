#!/usr/bin/env python3
"""
cn-epub-maker: Convert Chinese novel TXT files to professional vertical-layout EPUB.

Features:
- Auto-detect encoding (GBK/GB18030/UTF-8)
- Optional Simplified → Traditional Chinese conversion (via OpenCC)
- Detect and strip junk lines (ads, website headers/footers)
- Parse volume/chapter structure with customizable patterns
- Sequential chapter renumbering (fixes source numbering errors)
- Convert quotation marks to Traditional Chinese style 「」『』
- Convert Arabic numerals to Chinese numerals
- Vertical right-to-left layout with proper CSS
- RTL page progression for correct page turning
- Table of contents from volume headings

Dependencies:
- pandoc (required)
- opencc (optional, for Simplified → Traditional conversion)
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile


# ---------------------------------------------------------------------------
# Chinese numeral helpers
# ---------------------------------------------------------------------------

def int_to_chinese(n, digit_by_digit=False):
    """Convert integer to Chinese numeral.

    digit_by_digit=True for years (2008 → 二〇〇八).
    digit_by_digit=False for counts (1754 → 一千七百五十四).
    """
    if n == 0:
        return "〇"
    digits = "〇一二三四五六七八九"
    if digit_by_digit:
        return "".join(digits[int(d)] for d in str(n))
    parts = []
    if n >= 10000:
        parts.append(int_to_chinese(n // 10000))
        parts.append("萬")
        n %= 10000
        if 0 < n < 1000:
            parts.append("〇")
    if n >= 1000:
        parts.append(digits[n // 1000])
        parts.append("千")
        n %= 1000
        if 0 < n < 100:
            parts.append("〇")
    if n >= 100:
        parts.append(digits[n // 100])
        parts.append("百")
        n %= 100
        if 0 < n < 10:
            parts.append("〇")
    if n >= 10:
        if n // 10 > 1 or parts:
            parts.append(digits[n // 10])
        parts.append("十")
        n %= 10
    if n > 0:
        parts.append(digits[n])
    return "".join(parts)


# ---------------------------------------------------------------------------
# Text processing
# ---------------------------------------------------------------------------

def detect_encoding(filepath):
    """Try common Chinese encodings."""
    for enc in ["utf-8", "gb18030", "gbk", "big5"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8"


def read_and_convert(filepath, encoding, to_traditional):
    """Read file and optionally convert to Traditional Chinese."""
    with open(filepath, "r", encoding=encoding, errors="replace") as f:
        text = f.read()

    if to_traditional:
        proc = subprocess.run(
            ["opencc", "-c", "s2twp"],
            input=text,
            capture_output=True,
            text=True,
            check=True,
        )
        text = proc.stdout

    return text.splitlines()


def strip_junk(lines):
    """Remove junk header/footer lines (ads, website URLs, separator bars)."""
    junk_re = re.compile(
        r"^[=\-]{5,}$"           # separator bars like ========
        r"|https?://"             # URLs
        r"|www\."                 # URLs without scheme
        r"|精校.*小说"            # common ad phrases
        r"|下载.*小说"
        r"|本站.*提供"
        r"|书友.*推荐",
        re.IGNORECASE,
    )

    # Strip from top
    start = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if junk_re.search(s):
            start = i + 1
        else:
            break

    # Strip from bottom
    end = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        s = lines[i].strip()
        if not s:
            continue
        if junk_re.search(s):
            end = i
        else:
            break

    lines = lines[start:end]

    # Skip to first volume/chapter heading (skip synopsis etc.)
    for i, line in enumerate(lines):
        if re.match(r"^第.+[卷部冊章集篇回]", line.strip()):
            return lines[i:]

    return lines


def parse_structure(lines, volume_pat, chapter_pat, renumber):
    """Parse lines into structured Markdown with volume/chapter headings."""
    volume_re = re.compile(volume_pat)
    chapter_re = re.compile(chapter_pat)

    md_lines = []
    chapter_count = 0
    volume_count = 0

    for line in lines:
        stripped = line.strip()

        if not stripped:
            md_lines.append("")
            continue

        # Volume heading
        vm = volume_re.match(stripped)
        if vm:
            volume_count += 1
            vol_label = f"第{int_to_chinese(volume_count)}{vm.group('unit')}"
            title = vm.group("title").strip()
            md_lines.append("")
            md_lines.append(f"# {vol_label} {title}")
            md_lines.append("")
            continue

        # Chapter heading
        cm = chapter_re.match(stripped)
        if cm:
            chapter_count += 1
            title = cm.group("title").strip() if cm.group("title") else ""
            if renumber:
                label = f"第{int_to_chinese(chapter_count)}章"
            else:
                label = cm.group(0).split()[0] if cm.group(0) else f"第{int_to_chinese(chapter_count)}章"
                # Use original label up to title
                orig = cm.group(0)
                title_start = orig.find(title) if title else len(orig)
                label = orig[:title_start].strip()
            heading = f"## {label} {title}".strip()
            md_lines.append("")
            md_lines.append(heading)
            md_lines.append("")
            continue

        # Body text — remove leading full-width spaces (CSS handles indentation)
        text = stripped.lstrip("\u3000").strip()
        if text:
            md_lines.append(text)

    return md_lines, volume_count, chapter_count


def convert_punctuation(content):
    """Convert quotation marks to Traditional Chinese style."""
    content = content.replace("\u201c", "「").replace("\u201d", "」")
    content = content.replace("\u2018", "『").replace("\u2019", "』")
    return content


def convert_arabic_numbers(content):
    """Convert Arabic numerals to Chinese numerals."""

    def _replace(m):
        n = int(m.group(0))
        return int_to_chinese(n, digit_by_digit=(n >= 1000))

    return re.sub(r"[0-9]+", _replace, content)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

VERTICAL_CSS = """\
@charset "UTF-8";

html {
  writing-mode: vertical-rl;
  -webkit-writing-mode: vertical-rl;
}

body {
  font-family: "Songti TC", "Songti SC", "Noto Serif CJK TC",
               "Source Han Serif TC", serif;
  font-size: 1em;
  line-height: 1.8;
  margin: 1em;
  text-align: justify;
  text-orientation: mixed;
  -webkit-text-orientation: mixed;
}

nav#toc ol {
  list-style-type: none;
  padding-left: 0;
}

nav#toc li {
  margin-block-end: 0.3em;
}

h1 {
  font-size: 1.6em;
  font-weight: bold;
  margin-block-start: 3em;
  margin-block-end: 2em;
  text-align: center;
}

h2 {
  font-size: 1.3em;
  font-weight: bold;
  margin-block-start: 2em;
  margin-block-end: 1.5em;
  text-align: center;
}

p {
  text-indent: 2em;
  margin: 0;
  padding: 0;
}
"""

HORIZONTAL_CSS = """\
@charset "UTF-8";

body {
  font-family: "Songti SC", "Songti TC", "Noto Serif CJK SC",
               "Source Han Serif SC", serif;
  font-size: 1em;
  line-height: 1.8;
  margin: 1em;
  text-align: justify;
}

nav#toc ol {
  list-style-type: none;
  padding-left: 0;
}

h1 {
  font-size: 1.6em;
  font-weight: bold;
  margin-top: 2em;
  margin-bottom: 1em;
  text-align: center;
}

h2 {
  font-size: 1.3em;
  font-weight: bold;
  margin-top: 1.5em;
  margin-bottom: 1em;
  text-align: center;
}

p {
  text-indent: 2em;
  margin: 0;
  padding: 0;
}
"""


# ---------------------------------------------------------------------------
# EPUB building
# ---------------------------------------------------------------------------

def build_epub(md_path, epub_path, css_path, cover, title, author, lang, vertical):
    """Run pandoc to create EPUB, then patch for vertical layout."""
    cmd = [
        "pandoc", md_path,
        "-o", epub_path,
        "--toc",
        "--toc-depth=1",
        "--split-level=2",
        "--css", css_path,
        "--metadata", f"title={title}",
        "--metadata", f"author={author}",
        "--metadata", f"lang={lang}",
    ]
    if cover and os.path.isfile(cover):
        cmd += ["--epub-cover-image", cover]

    subprocess.run(cmd, check=True)

    if vertical:
        patch_epub_vertical(epub_path)


def patch_epub_vertical(epub_path):
    """Patch EPUB for RTL page progression and vertical styling on all pages."""
    tmpdir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(epub_path, "r") as zin:
            zin.extractall(tmpdir)

        for root, _dirs, files in os.walk(tmpdir):
            for f in files:
                fpath = os.path.join(root, f)
                if f.endswith(".opf"):
                    text = open(fpath, "r", encoding="utf-8").read()
                    text = text.replace(
                        '<spine toc="ncx">',
                        '<spine page-progression-direction="rtl" toc="ncx">',
                    )
                    open(fpath, "w", encoding="utf-8").write(text)
                elif f.endswith(".xhtml") and ("title" in f or "nav" in f):
                    html = open(fpath, "r", encoding="utf-8").read()
                    if "vertical-rl" not in html and "</head>" in html:
                        style = (
                            "<style>html, body { writing-mode: vertical-rl; "
                            "-webkit-writing-mode: vertical-rl; }</style>\n</head>"
                        )
                        html = html.replace("</head>", style)
                        open(fpath, "w", encoding="utf-8").write(html)

        # Repack (mimetype must be first and uncompressed per EPUB spec)
        with zipfile.ZipFile(epub_path, "w") as zout:
            mimetype = os.path.join(tmpdir, "mimetype")
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Convert Chinese novel TXT to professional EPUB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Simplest usage — auto-detect everything:
  %(prog)s novel.txt --title "書名" --author "作者"

  # GBK file → Traditional Chinese vertical EPUB with cover:
  %(prog)s novel.txt -t "書名" -a "作者" --cover cover.png

  # Already UTF-8 Traditional, no conversion, horizontal layout:
  %(prog)s novel.txt -t "書名" -a "作者" --no-convert --horizontal

  # Custom chapter pattern (e.g. 第X回):
  %(prog)s novel.txt -t "書名" -a "作者" --chapter-pattern "^(?P<label>第.+回)\\s*(?P<title>.*)"
""",
    )
    p.add_argument("input", help="Input TXT file path")
    p.add_argument("-o", "--output", help="Output EPUB path (default: <input>.epub)")
    p.add_argument("-t", "--title", required=True, help="Book title")
    p.add_argument("-a", "--author", required=True, help="Author name")
    p.add_argument("--cover", help="Cover image path (PNG/JPG)")
    p.add_argument("--lang", default="zh-Hant", help="Language tag (default: zh-Hant)")
    p.add_argument(
        "--encoding",
        help="Source file encoding (default: auto-detect)",
    )
    p.add_argument(
        "--no-convert",
        action="store_true",
        help="Skip Simplified → Traditional conversion",
    )
    p.add_argument(
        "--horizontal",
        action="store_true",
        help="Use horizontal layout instead of vertical",
    )
    p.add_argument(
        "--no-renumber",
        action="store_true",
        help="Keep original chapter numbers (don't renumber sequentially)",
    )
    p.add_argument(
        "--keep-arabic",
        action="store_true",
        help="Keep Arabic numerals (don't convert to Chinese)",
    )
    p.add_argument(
        "--keep-quotes",
        action="store_true",
        help='Keep original quotation marks (don\'t convert to 「」)',
    )
    p.add_argument(
        "--volume-pattern",
        default=r"^(?P<label>第.+(?P<unit>[卷部冊]))[\s　]+(?P<title>.+)$",
        help="Regex for volume headings (must have named groups: unit, title)",
    )
    p.add_argument(
        "--chapter-pattern",
        default=r"^(?P<label>第.+[章集篇回])[\s　]*(?P<title>.*)$",
        help="Regex for chapter headings (must have named group: title)",
    )

    args = p.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Paths
    base = os.path.splitext(args.input)[0]
    output = args.output or base + ".epub"
    md_path = base + "_processed.md"
    css_path = base + "_style.css"

    # 1. Read & convert
    encoding = args.encoding or detect_encoding(args.input)
    print(f"Reading {args.input} (encoding: {encoding})...")
    lines = read_and_convert(args.input, encoding, not args.no_convert)

    # 2. Strip junk
    print("Stripping junk lines...")
    lines = strip_junk(lines)

    # 3. Parse structure
    print("Parsing structure...")
    md_lines, vol_count, ch_count = parse_structure(
        lines, args.volume_pattern, args.chapter_pattern, not args.no_renumber
    )
    print(f"  Found {vol_count} volumes, {ch_count} chapters")

    # 4. Post-process
    content = "\n".join(md_lines)
    if not args.keep_quotes:
        print("Converting quotation marks...")
        content = convert_punctuation(content)
    if not args.keep_arabic:
        print("Converting Arabic numerals...")
        content = convert_arabic_numbers(content)
    content = re.sub(r"\n{3,}", "\n\n", content)

    # 5. Write markdown
    print(f"Writing {md_path}...")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f"title: {args.title}\n")
        f.write(f"author: {args.author}\n")
        f.write(f"lang: {args.lang}\n")
        if not args.horizontal:
            f.write("direction: rtl\n")
        f.write("---\n\n")
        f.write(content)

    # 6. Write CSS
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(HORIZONTAL_CSS if args.horizontal else VERTICAL_CSS)

    # 7. Build EPUB
    print(f"Building {output}...")
    build_epub(
        md_path, output, css_path, args.cover,
        args.title, args.author, args.lang,
        vertical=not args.horizontal,
    )
    print(f"Done! EPUB saved to {output}")

    # Cleanup intermediate files
    os.remove(md_path)
    os.remove(css_path)


if __name__ == "__main__":
    main()
