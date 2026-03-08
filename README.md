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

## Kindle 注音字型

本專案附帶修改版的**王漢宗中楷體注音**字型（`fonts/HanWangKaiMediumChuIn.ttf`），安裝到 Kindle 後，所有中文字都會自動顯示注音（ㄅㄆㄇㄈ）。

### 字型修改內容

此字型基於原版王漢宗中楷體注音，針對**直排顯示**做了以下優化：

- **標點符號字形替換**：所有標點（`，。！？：；…—、《》〈〉（）「」『』`）替換為宋體繁（Songti TC）的字形，確保直排時位置正確、無多餘注音
- **直排引號修正**：移除 `﹁﹂﹃﹄`（Unicode Vertical Presentation Forms）的字形映射，搭配 EPUB 內使用直排專用字符，Kindle 會用預設字型顯示引號（方向正確、不帶注音）

### 安裝方式

1. 用 USB 連接 Kindle
2. 將 `fonts/HanWangKaiMediumChuIn.ttf` 複製到 Kindle 根目錄的 `fonts` 資料夾（沒有就新建）
3. 開啟任意中文書 → 點 `Aa`（頁面顯示）→ 選擇「HanWangKaiMediumChuIn」字型

### 注意事項

- **破音字**：字型只顯示預設讀音，多音字（如「了」「地」「不」）不一定正確
- 僅支援 Kindle 實體裝置，不支援 Kindle App
- 原始字型由王漢宗教授捐贈，自由使用

## ToneOZ 注音字型（破音字支援）

本專案也附帶 **[澳聲通注音楷體](https://github.com/jeffreyxuan/toneoz-font-zhuyin)**（`fonts/ToneOZ-Zhuyin-Kai-Traditional.ttf`），基於思源宋體，採用 SIL Open Font License，無版權爭議。

### 破音字自動選音

搭配 `add_zhuyin_ivs.py` 腳本，可自動為 EPUB 中的破音字加入 IVS（異體字選擇器）標記。ToneOZ 字型會根據標記顯示正確的注音。

```bash
# 安裝依賴
pip install pypinyin
brew install opencc  # 用於簡繁轉換以提高破音字判斷準確度

# 為 EPUB 加入 IVS 標記
python3 add_zhuyin_ivs.py input.epub -o output_zhuyin.epub
```

### 原理

1. **pypinyin** 分析上下文，判斷每個破音字的正確讀音（如「銀行」的行 = ㄏㄤˊ）
2. 先轉簡體再分析，提高詞組匹配準確度
3. 查詢 `phonic_table_Z.txt` 對照表，找到對應的 IVS 選擇器
4. 在漢字後插入隱形的 Unicode 標記（如 `U+E01E1`）
5. ToneOZ 字型看到標記，顯示對應讀音的注音

### 字型修改內容

與王漢宗字型相同的直排優化：
- 標點符號字形替換為宋體繁，確保直排位置正確
- 移除 `﹁﹂﹃﹄` 字形映射，搭配直排引號修正

### 安裝方式

1. 用 USB 連接 Kindle
2. 將 `fonts/ToneOZ-Zhuyin-Kai-Traditional.ttf` 複製到 Kindle 的 `fonts` 資料夾
3. 開書 → `Aa` → 選擇「ToneOZ-Zhuyin-Kai-Traditional」字型

## 授權

MIT
