# cn-epub-maker

Convert Chinese novel TXT files to professional EPUB ebooks with vertical (直排) or horizontal layout.

## Features

- **Auto-detect encoding** — GBK, GB18030, UTF-8, Big5
- **Simplified → Traditional** conversion (via [OpenCC](https://github.com/BYVoid/OpenCC))
- **Vertical right-to-left layout** — proper `writing-mode: vertical-rl` with RTL page progression, like a real Chinese book
- **Smart junk removal** — auto-strips website ads, separator bars, and synopsis headers
- **Chapter structure parsing** — detects `第X卷`, `第X章`, `第X回`, etc.
- **Sequential renumbering** — fixes misnumbered/duplicate chapters in source files
- **Chinese typography** — converts `""` → `「」`, `''` → `『』`, Arabic → Chinese numerals
- **Cover image support**
- **Customizable** — volume/chapter patterns, encoding, layout direction

## Dependencies

```bash
# Required
brew install pandoc

# Optional (for Simplified → Traditional conversion)
brew install opencc
```

## Usage

```bash
# Basic — auto-detect encoding, convert to Traditional, vertical layout:
python3 cn_epub_maker.py novel.txt --title "書名" --author "作者"

# With cover image:
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" --cover cover.png

# Specify output path:
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" -o output.epub

# Already Traditional Chinese, skip conversion:
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" --no-convert

# Horizontal layout instead of vertical:
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" --horizontal

# Keep original chapter numbers (don't renumber):
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" --no-renumber

# Custom chapter pattern (e.g. 第X回 for classical novels):
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" \
  --chapter-pattern "^(?P<label>第.+回)[\s　]*(?P<title>.*)"

# Keep Arabic numerals and original quotes:
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" --keep-arabic --keep-quotes
```

## Options

| Flag | Description |
|------|-------------|
| `-t, --title` | Book title (required) |
| `-a, --author` | Author name (required) |
| `-o, --output` | Output EPUB path |
| `--cover` | Cover image (PNG/JPG) |
| `--lang` | Language tag (default: `zh-Hant`) |
| `--encoding` | Force source encoding |
| `--no-convert` | Skip Simplified → Traditional |
| `--horizontal` | Horizontal layout |
| `--no-renumber` | Keep original chapter numbers |
| `--keep-arabic` | Keep Arabic numerals |
| `--keep-quotes` | Keep original quotation marks |
| `--volume-pattern` | Custom volume heading regex |
| `--chapter-pattern` | Custom chapter heading regex |

## How It Works

1. **Read** the TXT file with auto-detected encoding
2. **Convert** to Traditional Chinese via OpenCC (optional)
3. **Strip** junk lines (ads, URLs, separators)
4. **Parse** volume/chapter structure into Markdown
5. **Renumber** chapters sequentially to fix source errors
6. **Convert** punctuation and numerals to Chinese style
7. **Generate** EPUB via pandoc with vertical CSS
8. **Patch** EPUB spine for RTL page progression

## Vertical Layout Details

The vertical EPUB follows the [好讀 (Haodoo) vertical EPUB guidelines](https://haodoo.org/?p=16765):

- `writing-mode: vertical-rl` on all pages including title and TOC
- `page-progression-direction="rtl"` in OPF spine
- Standard horizontal punctuation (readers auto-rotate)
- `text-orientation: mixed` for proper punctuation rendering
- Songti TC font stack for Traditional Chinese

## Kindle Zhuyin (Bopomofo) Font

This project includes a modified **HanWangKaiMediumChuIn** (王漢宗中楷體注音) font in `fonts/`. When installed on a Kindle, all Chinese characters automatically display with Zhuyin (ㄅㄆㄇㄈ) phonetic annotations.

### Font Modifications

This font is based on the original HanWangKaiMediumChuIn, optimized for **vertical text display**:

- **Punctuation glyph replacement**: All punctuation marks (`，。！？：；…—、《》〈〉（）「」『』`) are replaced with Songti TC (宋體繁) glyphs, ensuring correct positioning in vertical layout without unwanted Zhuyin annotations
- **Vertical bracket fix**: Removed glyph mappings for `﹁﹂﹃﹄` (U+FE41–FE44). When the EPUB uses these vertical presentation form characters, Kindle falls back to its default font (correct direction, no Zhuyin)

### Installation

1. Connect Kindle via USB
2. Copy `fonts/HanWangKaiMediumChuIn.ttf` to the `fonts` folder on Kindle root (create it if missing)
3. Open any Chinese book → tap `Aa` (Page Display) → select "HanWangKaiMediumChuIn"

### Notes

- **Polyphones**: The font shows only the default pronunciation; characters with multiple readings (e.g. 了、地、不) may not be accurate
- Works on Kindle hardware only, not the Kindle app
- Original font donated by Professor Wang Han-Tsung, free to use

## ToneOZ Zhuyin Font (Polyphone Support)

This project also includes **[ToneOZ Zhuyin Kai](https://github.com/jeffreyxuan/toneoz-font-zhuyin)** (`fonts/ToneOZ-Zhuyin-Kai-Traditional.ttf`), based on Source Han Serif under SIL Open Font License — no copyright concerns.

### Automatic Polyphone Detection

Use `add_zhuyin_ivs.py` to automatically add IVS (Ideographic Variation Selector) markers to EPUB files. The ToneOZ font reads these markers to display the correct pronunciation for polyphone characters.

```bash
# Install dependencies
pip install pypinyin
brew install opencc  # For T→S conversion to improve polyphone accuracy

# Add IVS markers to EPUB
python3 add_zhuyin_ivs.py input.epub -o output_zhuyin.epub
```

### How It Works

1. **pypinyin** analyzes context to determine correct pronunciation (e.g. 銀**行** = ㄏㄤˊ not ㄒㄧㄥˊ)
2. Converts to Simplified Chinese first for better phrase dictionary matching
3. Looks up `phonic_table_Z.txt` to find the matching IVS selector
4. Inserts invisible Unicode markers (e.g. `U+E01E1`) after each polyphone character
5. ToneOZ font reads the marker and displays the correct Zhuyin annotation

### Font Modifications

Same vertical optimizations as the HanWang font:
- Punctuation glyphs replaced with Songti TC for correct vertical positioning
- `﹁﹂﹃﹄` glyph mappings removed for vertical bracket workaround

### Installation

1. Connect Kindle via USB
2. Copy `fonts/ToneOZ-Zhuyin-Kai-Traditional.ttf` to Kindle's `fonts` folder
3. Open a book → tap `Aa` → select "ToneOZ-Zhuyin-Kai-Traditional"

## License

MIT
