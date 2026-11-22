#!/usr/bin/env python3
"""在正史底本中定位名单人物的本传，按人输出纯文本。

纪传体正史的列传卷以人物名为标题分节（宋史用 `== 黃庭堅 ==`，新唐書用
`= 錢徽 =`，附传用 `=== 附 孟郊 ===`），标题清洗后即为天然索引。标题失配时
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
HEADING = re.compile(r"^(={1,4}) (.+?) \1$", re.M)
# 同前缀页面（宋史全文、宋史紀事本末、四庫全書本）不是正卷，入索引会串书
VOLUME_PAGE = re.compile(r"^[^/]+/卷[零一二三四五六七八九十百〇0-9]+[上下中]?$")
# 标题里的注记：「子 璉」「弟 鍇」「附 孟郊」「從弟 審」
# 亲属前缀。必须带分隔符，否则「孫構」「曾鞏」这类姓名会被误当成附传标记
ATTACHED = re.compile(r"^(子|弟|兄|孫|曾孫|從子|從弟|從孫|族子|族弟|族孫|從父|族父|附)[:：\s]")
SEQ_SUFFIX = re.compile(r"(上|下|中)$")
VARIANT_CHARS = str.maketrans({"脩": "修", "濬": "浚", "叡": "睿", "褘": "禕", "沉": "沈", "眘": "昚", "勗": "勖"})
HAN = re.compile(r"[\u4e00-\u9fff]")
MIN_SECTION_CHARS = 80


def canonical(name: str) -> str:
    """异体字统一，否则「歐陽修」无法命中「歐陽脩」。"""
    return name.translate(VARIANT_CHARS)


def heading_name(raw: str) -> str:
    return ATTACHED.sub("", raw.strip())


def build_index(texts: dict[str, str]):
    """返回 (正名索引, 附传索引)。

    正名索引按人物姓名建键；附传索引处理「弟 肇」「從孫 祖禹」这类只写名不写姓
    的标题，用父级标题的姓氏补全后建键。
    """
    index: dict[str, list[tuple[str, str]]] = {}
    attached: dict[str, list[tuple[str, str]]] = {}
    for volume, text in texts.items():
        if not VOLUME_PAGE.match(volume):
            continue
        stack: list[tuple[int, str]] = []
        for match in HEADING.finditer(text):
            level = len(match.group(1))
            raw = match.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1] if stack else ""
            stack.append((level, raw))
            end = HEADING.search(text, match.end())
            body = text[match.end():end.start() if end else len(text)].strip()
            if len(body) < MIN_SECTION_CHARS:
                continue

            name = heading_name(raw)
            if HAN.search(name):
                key = canonical(SEQ_SUFFIX.sub("", name))
                index.setdefault(key, []).append((volume, body))

            # 附传标题只写名不写姓（「弟 肇」「從孫 祖禹」「太祖弟 魏悼王 廷美」），
            # 按名建键并记下父级姓氏，匹配时再用名单里的姓去核
            tokens = raw.split()
            if len(tokens) == 1 and not ATTACHED.match(raw):
                continue  # 普通姓名标题已在正名索引里
            tail = canonical(ATTACHED.sub("", tokens[-1]))
            if not tail or len(tail) >= 3:
                continue
            parent_surname = canonical(parent.split()[0][:1]) if parent else ""
            attached.setdefault(tail, []).append((volume, body, parent_surname))
    return index, attached


def locate(index, attached, texts, name: str):
    """按优先级定位：正名标题 → 附传标题 → 帝王本紀 → 正文特征串。"""
    key = canonical(name)
    if key in index:
        volume, body = max(index[key], key=lambda item: len(item[1]))
        return "heading", volume, body

    # 附传：父级姓氏与名单姓氏一致才算，防止同名异姓串人
    surname, given = canonical(name[:1]), canonical(name[1:])
    if given in attached:
        same = [item for item in attached[given] if item[2] in ("", surname)]
        if same:
            volume, body, _ = max(same, key=lambda item: len(item[1]))
            return "attached", volume, body

    # 本紀不以姓名立目，改用「某某皇帝，諱某」定位；返回整卷，本紀一卷即一朝
    if len(name) > 1:
        pattern = re.compile(r"皇帝[，,]?\s*諱" + re.escape(given))
        for volume, text in texts.items():
            if VOLUME_PAGE.match(volume) and pattern.search(text[:1200]):
                return "reign", volume, text.strip()

    pattern = re.compile(r"(?:^|\n)[\u3000\s]*" + re.escape(name) + r"[，,、]?\s*字[\u4e00-\u9fff]")
    for volume, text in texts.items():
        if not VOLUME_PAGE.match(volume):
            continue
        hit = pattern.search(text)
        if hit:
            return "inline", volume, text[hit.start():hit.start() + 4000].strip()
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
    print(f"名单 {len(roster)} 人 → {args.roster.name}")

    books = sorted({b for row in roster for b in BOOK_BY_DYNASTY.get(row["dynasty"].strip(), [])})
    raw = {}
    for book in books:
        path = args.sources / f"{book}.json"
        if not path.exists():
            raise FileNotFoundError(f"缺底本 {path}，先跑 01_fetchSources.py")
        raw[book] = json.loads(path.read_text(encoding="utf-8"))
    built = {book: build_index(texts) for book, texts in raw.items()}
    print("索引条目", {book: f"{len(idx)} 正名 / {len(att)} 附传" for book, (idx, att) in built.items()})

    args.out.mkdir(parents=True, exist_ok=True)
    # 手工补录的传记单独登记，重跑时不清除
    manual = {}
    manual_csv = args.out / "sourcesManual.csv"
    if manual_csv.exists():
        with manual_csv.open(encoding="utf-8-sig") as fh:
            manual = {row["person_id"]: row for row in csv.DictReader(fh)}
    kept = {f"{pid}_{row['name']}.txt" for pid, row in manual.items()}
    for stale in args.out.glob("*.txt"):
        if stale.name not in kept:
            stale.unlink()

    stats = Counter()
    manifest = []
    for row in roster:
        dynasty = row["dynasty"].strip()
        name = re.sub(r"[（(].*?[)）]", "", row["name"].strip())
        result = None
        for book in BOOK_BY_DYNASTY.get(dynasty, []):
            result = locate(*built[book], raw[book], name)
            if result:
                break
        mode, volume, body = result if result else ("", "", "")
        if not result and row["person_id"] in manual:
            entry = manual[row["person_id"]]
            path = args.out / f"{row['person_id']}_{row['name'].strip()}.txt"
            if path.exists():
                body = path.read_text(encoding="utf-8")
                result = ("manual", entry["source"], body)
                mode, volume = "manual", entry["source"]
        if mode == "attached":
            # 附传正文以名开头，补回姓氏后才可独立阅读
            body = re.sub(r"^(子|弟|兄|孫|曾孫|從子|從弟|從孫|族子|族弟|族孫|從父|族父|附)\s*"
                          + r"(?=" + re.escape(name[1:2]) + ")", "", body)
            body = body.lstrip("，,、　 ")
            if canonical(body[:1]) == canonical(name[1:2]):
                body = name[:1] + body
        if result:
            target = args.out / f"{row['person_id']}_{row['name'].strip()}.txt"
            target.write_text(body, encoding="utf-8")
            stats[(dynasty, "hit")] += 1
        else:
            stats[(dynasty, "miss")] += 1
        book = volume.split("·")[0] if mode == "manual" else volume.split("/")[0]
        manifest.append({"person_id": row["person_id"], "name": row["name"].strip(),
                         "dynasty": dynasty, "book": book, "volume": volume,
                         "mode": mode, "chars": len(body),
                         "status": "ok" if result else "missing",
                         "source": manual.get(row["person_id"], {}).get("source", "") if mode == "manual" else volume,
                         "note": manual.get(row["person_id"], {}).get("note", "")})

    with (args.out / "manifest.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(manifest[0].keys()))
        writer.writeheader()
        writer.writerows(manifest)

    total_hit, total = 0, 0
    for dynasty in sorted({k[0] for k in stats}):
        hit, span = stats[(dynasty, "hit")], sum(v for k, v in stats.items() if k[0] == dynasty)
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
