# cn-epub-maker

將中文小說 TXT 檔轉換為專業的直排（或橫排）EPUB 電子書。

[English](README.en.md)

## 功能特色

- **自動偵測編碼** — 支援 GBK、GB18030、UTF-8、Big5
- **簡體轉繁體** — 透過 [OpenCC](https://github.com/BYVoid/OpenCC) 自動轉換
- **直排右翻排版** — 正確的 `writing-mode: vertical-rl` 與 RTL 翻頁方向，如同實體中文書
- **智慧去除垃圾內容** — 自動清除網站廣告、分隔線、內容簡介等
- **章節結構解析** — 自動辨識 `第X卷`、`第X章`、`第X回` 等格式
- **章節重新編號** — 修正來源檔案中的章節編號錯誤與重複
- **中文排版規範** — `""` → `「」`、`''` → `『』`、阿拉伯數字轉中文數字
- **封面圖片支援**
- **高度自訂** — 可自訂卷/章正則表達式、編碼、排版方向

## 安裝依賴

```bash
# 必要
brew install pandoc

# 選用（簡轉繁功能需要）
brew install opencc
```

## 使用方式

```bash
# 基本用法 — 自動偵測編碼，轉繁體，直排輸出：
python3 cn_epub_maker.py novel.txt --title "書名" --author "作者"

# 加入封面圖片：
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" --cover cover.png

# 指定輸出路徑：
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" -o output.epub

# 來源已是繁體中文，跳過轉換：
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" --no-convert

# 使用橫排排版：
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" --horizontal

# 保留原始章節編號（不重新編號）：
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" --no-renumber

# 自訂章節格式（例如古典小說用「第X回」）：
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" \
  --chapter-pattern "^(?P<label>第.+回)[\s　]*(?P<title>.*)"

# 保留阿拉伯數字與原始引號：
python3 cn_epub_maker.py novel.txt -t "書名" -a "作者" --keep-arabic --keep-quotes
```

## 參數說明

| 參數 | 說明 |
|------|------|
| `-t, --title` | 書名（必填） |
| `-a, --author` | 作者（必填） |
| `-o, --output` | 輸出 EPUB 路徑 |
| `--cover` | 封面圖片（PNG/JPG） |
| `--lang` | 語言標籤（預設：`zh-Hant`） |
| `--encoding` | 強制指定來源編碼 |
| `--no-convert` | 跳過簡轉繁 |
| `--horizontal` | 使用橫排排版 |
| `--no-renumber` | 保留原始章節編號 |
| `--keep-arabic` | 保留阿拉伯數字 |
| `--keep-quotes` | 保留原始引號 |
| `--volume-pattern` | 自訂卷標題正則表達式 |
| `--chapter-pattern` | 自訂章標題正則表達式 |

## 運作原理

1. **讀取** TXT 檔案並自動偵測編碼
2. **轉換** 為繁體中文（透過 OpenCC，可選）
3. **清除** 垃圾內容（廣告、網址、分隔線）
4. **解析** 卷/章結構，轉為 Markdown
5. **重新編號** 章節，修正來源編號錯誤
6. **轉換** 標點符號與數字為中文格式
7. **生成** EPUB（透過 pandoc，搭配直排 CSS）
8. **修補** EPUB spine 的 RTL 翻頁方向

## 直排排版細節

本工具遵循[好讀直式 EPUB 製作規範](https://haodoo.org/?p=16765)：

- 所有頁面（含書名頁、目錄）皆套用 `writing-mode: vertical-rl`
- OPF spine 設定 `page-progression-direction="rtl"`
- 使用標準橫式標點（閱讀器會自動旋轉）
- `text-orientation: mixed` 確保標點正確顯示
- 宋體 TC 字型優先

## 授權

MIT
