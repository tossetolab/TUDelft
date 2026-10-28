# 辞書ファイルの使い方

重要語分析の精度は、この3ファイルを編集して育てます。

| ファイル | 役割 | 書き方 |
|---|---|---|
| `keep_terms.txt` | 1語として保持する複合語・専門用語（例: 3D都市モデル, PLATEAUマップ, 適地判定） | 1行1語。`#`はコメント |
| `stopwords.txt` | 分析から除外する一般語・定型語・ノイズ | 1行1語。`#`はコメント |
| `normalize.csv` | 表記ゆれの統一（例: OpenFORM→OpenFOAM） | `from,to,note` |

## 編集の指針
- **keep_terms**: 分割されて困る語を足す。長い語も短い語もOK（長い語が優先マッチ）。
- **stopwords**: 「頻出するが情報量が低い語」を足す。TF-IDFが全冊共通語を自動で抑えるので、消しすぎない。
- **normalize**: OCR由来のゆれ・全角半角・大文字小文字のゆれを統一。

## 再実行
```bash
python3 ../scripts/02_analyze_terms.py --work <workフォルダ> --dict . --topk 30
python3 ../scripts/03_build_xlsx.py --work <workフォルダ> --out <workフォルダ>/分析.xlsx
```
編集→再実行を繰り返して、特徴語・共起の結果を見ながら調整してください。

## 候補語の見つけ方
`corpus_freq.csv`（頻度順）を眺め、
- 割れている複合語 → keep_terms.txt へ
- 上位に来る無意味な語 → stopwords.txt へ
を移すのが効率的です。
