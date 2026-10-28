#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PLATEAU技術レポート 重要語分析パイプライン (Step 2, 外部辞書対応版)

入力: Step1が出力した txt フォルダ + manifest.csv
外部辞書(--dictフォルダ, 任意):
  keep_terms.txt … 1語として保護する複合語・専門用語
  stopwords.txt  … 分析から除外する語
  normalize.csv  … 表記ゆれ統一 (from,to,note)
処理:
  1. 正規化 → keep_terms保護 → fugashi(MeCab)形態素解析
     名詞・複合名詞(英数字を含む連続名詞)を抽出
  2. 全体頻度 / TF-IDF特徴語 / 共起 / 文書スコア
出力: corpus_freq.csv, feature_terms.csv, doc_scores.csv, cooccurrence.csv, terms_per_doc.json

使い方:
  python3 02_analyze_terms.py --work ./work [--dict ./dict] [--topk 30] [--minlen 2]
"""
import argparse, csv, json, math, os, re
from collections import Counter
import fugashi

tagger = fugashi.Tagger()

RE_SYMBOL = re.compile(r"^[\W_]+$")   # 記号のみ除外（英数字は複合語の一部として残す）
SENT_SPLIT = re.compile(r"[。\n]")


def load_lines(path):
    out = []
    if path and os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            s = ln.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out


def load_normalize(path):
    m = {}
    if path and os.path.exists(path):
        for r in csv.DictReader(open(path, encoding="utf-8-sig")):
            if r.get("from"):
                m[r["from"]] = r.get("to", "")
    return m


class Analyzer:
    def __init__(self, keep, stop, norm, minlen):
        self.keep = sorted(set(keep), key=len, reverse=True)   # 長い語から保護
        self.stop = set(stop)
        self.stop_lower = {s.lower() for s in stop}
        self.norm = norm
        self.minlen = minlen
        # keep語を1トークンとして切り出す正規表現（長い語優先）
        self.keep_re = re.compile("|".join(re.escape(t) for t in self.keep)) if self.keep else None

    def normalize(self, text):
        for a, b in self.norm.items():
            if a:
                text = text.replace(a, b)
        return text

    def _ok(self, term):
        if len(term) < self.minlen or term in self.stop:
            return False
        if term.isdigit():                       # 純数字（23, 2023 等）は除外
            return False
        if re.fullmatch(r"[A-Za-z]{1,2}", term):  # 1-2文字の英字（uc, FN等）は除外
            return False
        if term.lower() in self.stop_lower:       # 大小文字を無視した除外
            return False
        return True

    def _nouns_from_text(self, seg):
        """MeCabで名詞・複合名詞(英数字含む連続名詞)を抽出。plain textセグメント用。"""
        terms, cur = [], []
        toks = list(tagger(seg))
        for w in toks:
            s = w.surface
            if w.feature.pos1 == "名詞" and not RE_SYMBOL.match(s):
                cur.append(s)
            elif cur:
                term = "".join(cur)
                if self._ok(term):
                    terms.append(term)
                cur = []
        if cur:
            term = "".join(cur)
            if self._ok(term):
                terms.append(term)
        # 単独名詞も個別に（複合語の構成要素も拾う）
        for w in toks:
            s = w.surface
            if w.feature.pos1 == "名詞" and not RE_SYMBOL.match(s) and self._ok(s):
                terms.append(s)
        return terms

    def extract(self, text):
        text = self.normalize(text)
        doc_terms, sent_lists = [], []
        for sent in SENT_SPLIT.split(text):
            if not sent.strip():
                continue
            terms = []
            if self.keep_re:
                pos = 0
                for m in self.keep_re.finditer(sent):
                    if m.start() > pos:
                        terms += self._nouns_from_text(sent[pos:m.start()])
                    kw = m.group()                 # keep語はそのまま1語
                    if self._ok(kw):
                        terms.append(kw)
                    pos = m.end()
                if pos < len(sent):
                    terms += self._nouns_from_text(sent[pos:])
            else:
                terms = self._nouns_from_text(sent)
            if terms:
                sent_lists.append(terms)
                doc_terms.extend(terms)
        return doc_terms, sent_lists


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--dict", default=None, help="辞書フォルダ(keep_terms/stopwords/normalize)")
    ap.add_argument("--topk", type=int, default=30)
    ap.add_argument("--minlen", type=int, default=2)
    args = ap.parse_args()

    keep = stop = []
    norm = {}
    if args.dict:
        keep = load_lines(os.path.join(args.dict, "keep_terms.txt"))
        stop = load_lines(os.path.join(args.dict, "stopwords.txt"))
        norm = load_normalize(os.path.join(args.dict, "normalize.csv"))
    az = Analyzer(keep, stop, norm, args.minlen)
    print(f"辞書: keep={len(keep)} stop={len(stop)} normalize={len(norm)}")

    txt_dir = os.path.join(args.work, "txt")
    manifest = list(csv.DictReader(open(os.path.join(args.work, "manifest.csv"), encoding="utf-8-sig")))

    docs, doc_sentences = {}, {}
    for row in manifest:
        stem = row["stem"]
        text = open(os.path.join(txt_dir, stem + ".txt"), encoding="utf-8").read()
        terms, sents = az.extract(text)
        docs[stem] = Counter(terms)
        doc_sentences[stem] = sents

    N = len(docs)
    df = Counter()
    for c in docs.values():
        for t in c:
            df[t] += 1
    total = Counter()
    for c in docs.values():
        total.update(c)

    with open(os.path.join(args.work, "corpus_freq.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["term", "total_count", "doc_freq"])
        for t, cnt in total.most_common():
            w.writerow([t, cnt, df[t]])

    tfidf = {}
    for stem, c in docs.items():
        maxtf = max(c.values()) if c else 1
        tfidf[stem] = {t: (tf / maxtf) * (math.log((N + 1) / (df[t] + 1)) + 1)
                       for t, tf in c.items()}

    title_map = {r["stem"]: r["title"] for r in manifest}
    with open(os.path.join(args.work, "feature_terms.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["stem", "title", "rank", "term", "tfidf", "count"])
        for stem, sc in tfidf.items():
            for rank, (t, s) in enumerate(sorted(sc.items(), key=lambda x: -x[1])[: args.topk], 1):
                w.writerow([stem, title_map.get(stem, ""), rank, t, round(s, 4), docs[stem][t]])

    with open(os.path.join(args.work, "doc_scores.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stem", "title", "n_terms", "n_unique_terms", "top_tfidf_sum", "top3_terms"])
        for stem in docs:
            ranked = sorted(tfidf[stem].items(), key=lambda x: -x[1])
            w.writerow([stem, title_map.get(stem, ""), sum(docs[stem].values()), len(docs[stem]),
                        round(sum(s for _, s in ranked[: args.topk]), 3),
                        " / ".join(t for t, _ in ranked[:3])])

    co = Counter()
    for sents in doc_sentences.values():
        for terms in sents:
            uniq = sorted(set(terms))
            for i in range(len(uniq)):
                for j in range(i + 1, len(uniq)):
                    co[(uniq[i], uniq[j])] += 1
    with open(os.path.join(args.work, "cooccurrence.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["term1", "term2", "cooccur_count"])
        for (a, b), cnt in co.most_common(300):
            if cnt >= 3:
                w.writerow([a, b, cnt])

    with open(os.path.join(args.work, "terms_per_doc.json"), "w", encoding="utf-8") as f:
        json.dump({s: dict(c.most_common(100)) for s, c in docs.items()}, f, ensure_ascii=False, indent=1)

    print(f"分析完了: {N}冊, ユニーク語 {len(df)}, 全体延べ {sum(total.values())}")


if __name__ == "__main__":
    main()
