# PLATEAUdocs_keyword_analysis

国土交通省 **Project PLATEAU** の技術検証レポート（全113冊）を対象に、日本語テキストマイニングで重要語を抽出・可視化するための分析パイプラインです。PDF からのテキスト抽出、形態素解析による名詞・複合名詞の抽出、頻度・TF-IDF・共起の集計、Excel への集約までを 3 本の Python スクリプトで行います。

---

## 概要

| 項目 | 値 |
|---|---|
| 対象 | PLATEAU 技術検証レポート 113冊（`plateau_tech_doc_XXXX_verNN.pdf`） |
| 総ページ数 | 18,290 ページ |
| 抽出文字数 | 約 965 万字（1冊あたり平均 約 85,000 字、最小 9,225 / 最大 352,731） |
| 延べ抽出語数 | 約 257 万語 |
| 異なり語数 | 約 13.1 万語 |
| 抽出失敗 | 0冊（全冊にテキスト層があり、OCR は不要） |

---

## 分析の流れ

```
PDF（113冊）
  │  01_extract_pdf.py   … PyMuPDF でテキスト層を抽出・定型句除去・タイトル推定
  ▼
txt/*.txt + manifest.csv
  │  02_analyze_terms.py … 辞書適用 → fugashi(MeCab) 形態素解析 → 頻度 / TF-IDF / 共起 / 文書スコア
  ▼
corpus_freq.csv / feature_terms.csv / doc_scores.csv / cooccurrence.csv / terms_per_doc.json
  │  03_build_xlsx.py    … openpyxl で 1 冊の Excel ブックに集約（グラフ付き）
  ▼
PLATEAU重要語分析_全113冊.xlsx
```

---

## 使用ツール

| ツール | 用途 |
|---|---|
| Python 3 | 実行環境 |
| [PyMuPDF](https://pymupdf.readthedocs.io/)（`fitz`） | PDF のテキスト抽出、表紙のフォントサイズ情報によるタイトル推定 |
| [fugashi](https://github.com/polm/fugashi)（MeCab ラッパー） | 日本語形態素解析（品詞 `pos1 == 名詞` の判定） |
| unidic-lite（または UniDic） | fugashi が使う辞書 |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel ブックの生成（書式設定・棒グラフ） |
| 標準ライブラリ | `csv`, `json`, `re`, `math`, `collections.Counter` |

### インストール

```bash
pip install -r requirements.txt
```

---

## 分析手法

### Step 1：PDF テキスト抽出（`scripts/01_extract_pdf.py`）

- PyMuPDF で各ページのテキスト層を取得し、**1冊 = 1テキストファイル** として `txt/` に保存します。
- 次の行を除去して正規化します。
  - `Copyright © … reserved` の定型フッター
  - ページ番号のみの行、空行
- **タイトル推定**：表紙ページで最大フォントサイズ（最大値の 95% 以上）の行を連結し、日本語を含む行を優先します。数字のみ・短すぎる・日本語を含まない場合は、冒頭 2 ページから「技術検証レポート」「システム」「シミュレーション」などのキーワードを含む 6〜50 文字の行を代替タイトルとして採用します。
- ファイル名・タイトル・ページ数・文字数を `manifest.csv` に記録します。

```bash
python3 scripts/01_extract_pdf.py --src <PDFフォルダ> --out <workフォルダ> [--limit 5] [--files a.pdf b.pdf]
```

### Step 2：重要語分析（`scripts/02_analyze_terms.py`）

#### 2-1. 前処理と語の抽出

1. **表記ゆれの正規化**：`dict/normalize.csv` に従って置換します（例：`OpenFORM → OpenFOAM`、`ユーザインタフェース → ユーザインターフェース`）。
2. **専門用語の保護**：`dict/keep_terms.txt` の語を、形態素解析の前に正規表現で 1 トークンとして切り出します（長い語を優先してマッチ）。これにより「3D都市モデル」「PLATEAUマップ」などが分割されるのを防ぎます。
3. **形態素解析**：残りの部分を fugashi(MeCab) で解析し、
   - 連続する名詞を連結した **複合名詞**（英数字を含む連続名詞も対象）
   - 複合名詞の構成要素となる **単独名詞**
   の両方を抽出します。
4. **除外ルール**：次の語は集計から除きます。
   - `dict/stopwords.txt` に記載された語（大文字・小文字は区別しない）
   - 最小文字数（`--minlen`、既定 2）未満の語
   - 純数字（`23`、`2023` など）
   - 1〜2 文字の英字（`uc`、`FN` など）
   - 記号のみの語
5. 文は `。` と改行で区切り、共起計算の単位とします。

#### 2-2. 指標

| 指標 | 計算方法 | 出力 |
|---|---|---|
| 全体頻度 | コーパス全体の総出現回数と出現文書数（DF） | `corpus_freq.csv` |
| TF-IDF | `TF = tf / max_tf`（文書内最大頻度で正規化）<br>`IDF = log((N+1)/(df+1)) + 1`（スムージング付き）<br>`TF-IDF = TF × IDF` | `feature_terms.csv`（文書ごとに上位 `--topk` 語、既定 30） |
| 文書スコア | 延べ語数、異なり語数、TF-IDF 上位 `topk` 語の合計（＝特徴の強さ）、代表語トップ3 | `doc_scores.csv` |
| 共起 | 同一文内に現れる異なり語ペアを数え上げ、上位 300 ペアのうち共起回数 3 以上を出力 | `cooccurrence.csv` |
| 文書別語頻度 | 各文書の上位 100 語 | `terms_per_doc.json` |

TF-IDF は全冊に共通する語の重みを自動的に下げるため、「データ」「機能」「システム」のような基盤語ではなく、各レポート固有の技術や対象（例：除雪、ドローン、浸水）が上位に来ます。文書スコアを使うと、特徴が際立った文書と汎用的な文書を数値で区別できます。

```bash
python3 scripts/02_analyze_terms.py --work <workフォルダ> --dict dict --topk 30 --minlen 2
```

### Step 3：Excel への集約（`scripts/03_build_xlsx.py`）

Step 2 の CSV を 1 冊の Excel ブックにまとめます。

| シート | 内容 |
|---|---|
| 概要 | 対象・処理手順・指標の説明 |
| 文書一覧＆スコア | 文書ごとの語数、特徴強度、代表語 |
| 全体頻出語 | 上位 200 語と頻出語上位 20 の横棒グラフ |
| 特徴語(文書別) | 文書ごとの TF-IDF 上位語 |
| 共起ペア | 同一文中の共起ペアと回数 |

```bash
python3 scripts/03_build_xlsx.py --work <workフォルダ> --out <workフォルダ>/分析.xlsx
```

> 注：「概要」シートの説明文は試作時（5冊）の文言がスクリプト内に固定で書かれています。全冊で再生成する場合は `notes` の内容を適宜書き換えてください。

---

## 辞書（`dict/`）

分析精度は 3 つの辞書ファイルを編集して高めます。詳細は [`dict/README.md`](dict/README.md) を参照してください。

| ファイル | 役割 | 形式 |
|---|---|---|
| `keep_terms.txt` | 1 語として保持する複合語・専門用語（例：3D都市モデル、PLATEAUマップ、適地判定） | 1 行 1 語、`#` はコメント |
| `stopwords.txt` | 分析から除外する一般語・定型語・ノイズ | 1 行 1 語、`#` はコメント |
| `normalize.csv` | 表記ゆれの統一 | `from,to,note` |

**調整の進め方**：`corpus_freq.csv` を頻度順に眺め、分割されてしまった複合語は `keep_terms.txt` へ、上位に来る情報量の低い語は `stopwords.txt` へ移して Step 2・3 を再実行します。TF-IDF が全冊共通語を自動で抑えるため、ストップワードは入れすぎないのがコツです。

---

## ディレクトリ構成

```
PLATEAUdocs_keyword_analysis/
├── README.md
├── requirements.txt
├── .gitignore
├── scripts/
│   ├── 01_extract_pdf.py        # Step 1: PDF → テキスト
│   ├── 02_analyze_terms.py      # Step 2: 形態素解析・各指標
│   └── 03_build_xlsx.py         # Step 3: Excel 集約
├── dict/
│   ├── README.md
│   ├── keep_terms.txt
│   ├── stopwords.txt
│   └── normalize.csv
├── txt/                         # 抽出テキスト（※リポジトリには含めない。Step 1 で生成）
├── manifest.csv                 # 冊ごとのメタデータ
├── corpus_freq.csv              # 全体頻度・DF
├── feature_terms.csv            # 文書別 TF-IDF 特徴語
├── doc_scores.csv               # 文書スコア
├── cooccurrence.csv             # 共起ペア
├── PLATEAU重要語分析_全113冊.xlsx
├── PLATEAU重要語分析_試作.xlsx   # 試作（5冊）
├── 分析レポート_全113冊.md
├── 分析レポート_試作.md
├── wordcloud_en.png             # 頻出語ワードクラウド（英訳ラベル）
├── wordcloud_content_en.png     # 一般語を除いた内容語のワードクラウド
├── PLATEAU_frequent_terms.pptx  # 発表用スライド（頻出語）
├── PLATEAU_content_terms.pptx   # 発表用スライド（内容語）
└── oral_script_EN.md            # 上記スライドの英語発表原稿
```

---

## 主な結果

- **全体頻出語**：データ、機能、システム、表示、情報、技術、開発、形式、作成、建物、画面、モデル、設定、3D都市モデル。いずれも 100 冊以上に現れる、PLATEAU レポート共通の基盤語です。
- **内容語**（DF ≧ 110 の全冊共通語を除いた上位）：シミュレーション、申請、施設、インタフェース、参加、登録、判定、フローチャート、景観、地下、まちづくり、BIM、解析、浸水、ワークショップ など。
- **文書別特徴語（TF-IDF）の例**

| レポート | 特徴語トップ |
|---|---|
| 災害廃棄物発生量シミュレーション | 廃棄 / 置場 / 災害廃棄 |
| 3D都市モデルとBIMを活用したドローン運航 | ドローン / 運航 / BIM |
| 豪雪地帯の除雪優先度算出システム | 除雪 / 積雪 / 被災現場支援ツール |
| CityGML 3.0 概要（技術資料） | 地物 / モジュール / Dynamizer |
| XR体感型アーバンプランニング | タンジブル / AR / VR |
| 水害対策アプリケーション | 浸水 / 避難 / Re:Earth |

詳細は `分析レポート_全113冊.md` と Excel ブックを参照してください。

---

## クイックスタート

```bash
# 0. 依存パッケージのインストール
pip install -r requirements.txt

# 1. PDF からテキストを抽出（PDF は PLATEAU サイトから各自入手）
python3 scripts/01_extract_pdf.py --src /path/to/PLATEAUdocs --out ./work

# 2. 重要語分析（辞書を適用）
python3 scripts/02_analyze_terms.py --work ./work --dict ./dict --topk 30

# 3. Excel ブックを作成
python3 scripts/03_build_xlsx.py --work ./work --out ./work/PLATEAU重要語分析.xlsx
```

---

## 既知の制約・注意点

- **共起の上位**：全冊が同じ体裁のため、「レポート」「技術」「技術検証レポート」の組み合わせが共起上位を占めます。テーマ間のつながりを見たい場合は、これらを `stopwords.txt` に加えて再実行してください。
- **ユースケース ID**（`UC23` など）や体裁語は、分析目的に応じてストップワードへの追加を検討してください。
- **タイトル推定**：表紙が画像の文書（0057）は個別に修正しています。
- **字形のゆれ**：PDF 由来の CJK 互換字形（例：`⾞` U+2F9E と `車`）が残る場合があります。必要に応じて `normalize.csv` に追加するか、Unicode NFKC 正規化を加えてください。
- **ワードクラウドとスライド**：`wordcloud_*.png`、`*.pptx` は Step 2 の結果をもとに別途作成したもので、生成スクリプトは本リポジトリに含まれていません。
- 複合名詞とその構成要素の単独名詞を両方数えるため、構成要素の頻度は高めに出ます。

---

## データの出典と利用条件

分析対象は国土交通省 Project PLATEAU が公開している技術検証レポートです。

- Project PLATEAU：https://www.mlit.go.jp/plateau/

レポート本文の抽出テキスト（`txt/`）と元の PDF は、本リポジトリでは再配布しません（`.gitignore` で除外しています）。分析を再現する場合は、PLATEAU サイトから技術検証レポートの PDF を入手し、Step 1 を実行して `txt/` と `manifest.csv` を生成してください。集計結果（CSV・Excel など）を利用する際は、出典として Project PLATEAU（国土交通省）を表示してください。

---

## ライセンス

（未定：例として、スクリプトは MIT License、分析結果は CC BY 4.0 など）

## 作成者

Tosseto（駒澤大学）
