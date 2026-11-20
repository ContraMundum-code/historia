#!/usr/bin/env python3
"""在正史底本中定位名单人物的本传，按人输出纯文本。

纪传体正史的列传卷以人物名为标题分节（宋史用 `==黃庭堅==`，新唐書用
`=錢徽=`，附传用 `===附 孟郊===`），标题清洗后即为天然索引。标题失配时
退回「人名，字某某」的正文特征串，覆盖标题写法不规范或有异体字的情形。

用法：
    python scripts/corpus/02_extractBiographies.py
    python scripts/corpus/02_extractBiographies.py --roster .scratch/workload/personA.csv
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BOOK_BY_DYNASTY = {"唐": ["舊唐書", "新唐書"], "宋": ["宋史"], "明": ["明史"]}
HEADING = re.compile(r"^(={1,4})\s*([^=\n]+?)\s*\1\s*$", re.M)
# 同前缀页面（宋史全文、宋史紀事本末、四庫全書本）不是正卷，入索引会串书
VOLUME_PAGE = re.compile(r"^[^/]+/卷[零一二三四五六七八九十百〇0-9]+[上下中]?$")
HEADING_CLEAN = (
    (re.compile(r"^-\{(.*)\}-$"), r"\1"),          # -{范仲淹}- 繁简转换标记
    (re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]"), r"\1"),  # [[w:X|X]]
    (re.compile(r"<[^>]+>"), ""),
    (re.compile(r"\{\{[^}]*\}\}"), ""),
    (re.compile(r"^[（(].*?[)）]\s*"), ""),
    (re.compile(r"^附[:：]?\s*"), ""),
)
SEQ_SUFFIX = re.compile(r"(上|下|中)$")
VARIANT_CHARS = str.maketrans({"脩": "修", "濬": "浚", "叡": "睿", "褘": "禕"})
HAN = re.compile(r"[\u4e00-\u9fff]")
MIN_SECTION_CHARS = 80


def canonical(name: str) -> str:
    """异体字统一，否则「歐陽修」无法命中「歐陽脩」。"""
    return name.translate(VARIANT_CHARS)


def clean_heading(raw: str) -> str:
    text = raw.strip()
    for pattern, repl in HEADING_CLEAN:
        text = pattern.sub(repl, text)
    text = text.replace("-{", "").replace("}-", "")
    return re.split(r"[　\s]", text.strip())[0]


def build_index(texts: dict[str, str]) -> dict[str, list[tuple[str, str]]]:
    """人名 -> [(卷题, 正文)]，同名的多卷条目全部保留。"""
    index: dict[str, list[tuple[str, str]]] = {}
    for volume, wikitext in texts.items():
        if not VOLUME_PAGE.match(volume):
            continue
        wikitext = re.sub(r"\{\{textquality[^}]*\}\}", "", wikitext)
        parts = HEADING.split(wikitext)
        # split 捕获分隔符后三元一组：分隔符、标题、正文
        for i in range(1, len(parts) - 2, 3):
            name = clean_heading(parts[i + 1])
            body = parts[i + 2]
            if not HAN.search(name) or len(body) < MIN_SECTION_CHARS:
                continue
            key = canonical(SEQ_SUFFIX.sub("", name))
            index.setdefault(key, []).append((volume, body))
    return index


def locate(index: dict[str, list[tuple[str, str]]], texts: dict[str, str],
           name: str) -> tuple[str, str, str] | None:
    """返回 (匹配方式, 卷题, 正文)；标题优先，正文特征串兜底。"""
    key = canonical(name)
    if key in index:
        volume, body = max(index[key], key=lambda item: len(item[1]))
        return "heading", volume, body
    pattern = re.compile(r"(?:^|\n)[\u3000\s]*" + re.escape(name) + r"[，,、]?\s*字[\u4e00-\u9fff]")
    for volume, wikitext in texts.items():
        if not VOLUME_PAGE.match(volume):
            continue
        hit = pattern.search(wikitext)
        if hit:
            return "inline", volume, wikitext[hit.start():hit.start() + 4000].strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", type=Path,
                        default=ROOT / ".scratch" / "workload" / "personA.csv")
    parser.add_argument("--sources", type=Path, default=ROOT / ".scratch" / "sources")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "corpus")
    args = parser.parse_args()

    with args.roster.open(encoding="utf-8-sig") as fh:
        roster = list(csv.DictReader(fh))
    print(f"名单 {len(roster)} 人 → {args.roster}")

    books = sorted({b for row in roster for b in BOOK_BY_DYNASTY.get(row["dynasty"].strip(), [])})
    raw = {}
    for book in books:
        path = args.sources / f"{book}.json"
        if not path.exists():
            raise FileNotFoundError(f"缺底本 {path}，先跑 01_fetchSources.py")
        raw[book] = json.loads(path.read_text(encoding="utf-8"))
    index = {book: build_index(texts) for book, texts in raw.items()}
    print("索引条目", {book: len(idx) for book, idx in index.items()})

    args.out.mkdir(parents=True, exist_ok=True)
    for stale in args.out.glob("*.txt"):
        stale.unlink()

    stats = Counter()
    manifest = []
    for row in roster:
        dynasty = row["dynasty"].strip()
        name = re.sub(r"[（(].*?[)）]", "", row["name"].strip())
        result = None
        for book in BOOK_BY_DYNASTY.get(dynasty, []):
            result = locate(index[book], raw[book], name)
            if result:
                break
        mode, volume, body = result if result else ("", "", "")
        if result:
            target = args.out / f"{row['person_id']}_{row['name'].strip()}.txt"
            target.write_text(body, encoding="utf-8")
            stats[(dynasty, "hit")] += 1
        else:
            stats[(dynasty, "miss")] += 1
        manifest.append({"person_id": row["person_id"], "name": row["name"].strip(),
                         "dynasty": dynasty, "book": volume.split("/")[0],
                         "volume": volume, "mode": mode, "chars": len(body),
                         "status": "ok" if result else "missing"})

    with (args.out / "manifest.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(manifest[0].keys()))
        writer.writeheader()
        writer.writerows(manifest)

    total_hit, total = 0, 0
    for dynasty in sorted({k[0] for k in stats}):
        hit = stats[(dynasty, "hit")]
        span = hit + stats[(dynasty, "miss")]
        total_hit += hit
        total += span
        print(f"{dynasty}: {hit}/{span} = {hit / span:.1%}")
    print(f"合计 {total_hit}/{total} = {total_hit / total:.1%}")
    print("未命中：", [m["name"] for m in manifest if m["status"] == "missing"])
    lengths = [m["chars"] for m in manifest if m["chars"]]
    if lengths:
        print(f"正文长度 中位 {sorted(lengths)[len(lengths) // 2]} / 最长 {max(lengths)} 字")
    print(f"输出目录 {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
