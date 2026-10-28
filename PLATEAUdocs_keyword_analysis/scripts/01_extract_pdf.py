#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PLATEAU技術レポート テキスト抽出パイプライン (Step 1)

- 指定フォルダのPDFからテキスト層を抽出
- 1冊 = 1テキストファイル (out_dir/*.txt) として保存
- ヘッダー/フッター(Copyright等)や空白を正規化
- メタデータ(ファイル名/タイトル/ページ数/文字数)を manifest.csv に出力

使い方:
  python3 01_extract_pdf.py --src <PDFフォルダ> --out <出力フォルダ> [--limit 5] [--files a.pdf b.pdf]
"""
import argparse, csv, os, re, sys, glob
import fitz  # PyMuPDF（高速なテキスト抽出）

# 各ページ末尾などに繰り返し現れる定型句を除去
FOOTER_PATTERNS = [
    re.compile(r"Copyright\s*©.*?reserved\.?", re.I),
    re.compile(r"^\s*\d+\s*$"),  # ページ番号のみの行
]

def clean_text(text: str) -> str:
    lines = []
    for ln in text.splitlines():
        s = ln.rstrip()
        if not s.strip():
            continue
        drop = False
        for pat in FOOTER_PATTERNS:
            if pat.search(s):
                drop = True
                break
        if drop:
            continue
        lines.append(s)
    return "\n".join(lines)

def _cover_title(page):
    """表紙で最大フォントの日本語行をタイトルとして推定。"""
    spans = []  # (size, text)
    try:
        d = page.get_text("dict")
    except Exception:
        return ""
    for block in d.get("blocks", []):
        for line in block.get("lines", []):
            txt = "".join(sp.get("text", "") for sp in line.get("spans", [])).strip()
            if not txt or "Copyright" in txt or "MLIT" in txt:
                continue
            size = max((sp.get("size", 0) for sp in line.get("spans", [])), default=0)
            spans.append((size, txt))
    if not spans:
        return ""
    maxsize = max(s for s, _ in spans)
    # 最大フォント帯（95%以上）の行を連結。日本語を含むものを優先。
    cand = [t for s, t in spans if s >= maxsize * 0.95]
    jp = [t for t in cand if re.search(r"[぀-ヿ一-鿿]", t)]
    picked = jp if jp else cand
    return " ".join(picked[:2]).strip()


def extract_one(path: str):
    pages_text = []
    doc = fitz.open(path)
    n_pages = doc.page_count
    title = _cover_title(doc[0]) if n_pages else ""
    for page in doc:
        pages_text.append(page.get_text() or "")
    doc.close()
    # タイトルが数字のみ/短すぎ/非日本語なら、本文冒頭から題名らしい行を探す
    def _bad(t):
        return (not t) or len(t) < 6 or not re.search(r"[぀-ヿ一-鿿]", t) \
            or re.fullmatch(r"[Nno.\s\d]+", t) is not None
    KW = re.compile(r"(技術検証レポート|レポート|システム|ツール|シミュレーション|"
                    r"プラグイン|支援|構築|開発|技術|プランニング|ダッシュボード|可視化|活用)")
    if _bad(title):
        head = "\n".join(pages_text[:2])
        best = ""
        for ln in head.splitlines():
            s = ln.strip()
            if 6 <= len(s) <= 50 and re.search(r"[぀-ヿ一-鿿]", s) \
               and "Copyright" not in s and KW.search(s):
                best = s
                break
        if best:
            title = best
    raw = "\n".join(pages_text)
    cleaned = clean_text(raw)
    return {"title": title, "n_pages": n_pages, "text": cleaned}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0, help="先頭N件のみ(0=全件)")
    ap.add_argument("--files", nargs="*", default=None, help="対象ファイル名を明示指定")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    txt_dir = os.path.join(args.out, "txt")
    os.makedirs(txt_dir, exist_ok=True)

    if args.files:
        paths = [os.path.join(args.src, f) for f in args.files]
    else:
        paths = sorted(glob.glob(os.path.join(args.src, "*.pdf")))
        if args.limit:
            paths = paths[: args.limit]

    manifest = []
    for p in paths:
        name = os.path.basename(p)
        stem = os.path.splitext(name)[0]
        try:
            r = extract_one(p)
        except Exception as e:
            print(f"[ERROR] {name}: {e}", file=sys.stderr)
            continue
        out_txt = os.path.join(txt_dir, stem + ".txt")
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(r["text"])
        manifest.append({
            "file": name,
            "stem": stem,
            "title": r["title"],
            "n_pages": r["n_pages"],
            "n_chars": len(r["text"]),
        })
        print(f"[OK] {name}  pages={r['n_pages']}  chars={len(r['text'])}  title={r['title'][:40]}")

    with open(os.path.join(args.out, "manifest.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "stem", "title", "n_pages", "n_chars"])
        w.writeheader()
        w.writerows(manifest)
    print(f"\n抽出完了: {len(manifest)}冊 -> {txt_dir}")

if __name__ == "__main__":
    main()
