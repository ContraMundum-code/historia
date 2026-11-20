#!/usr/bin/env python3
"""从 CBDB 离线库导出项目需要的三张表。

清洗规则:只保留唐、宋、明三朝,且生年与卒年都齐全的人物。
这样每条记录的 birth_year / death_year 都可用,后续算年龄、排时间线不用再做缺失处理。

产出::

    data/dictionaries/person.csv     人物
    data/dictionaries/alias.csv      别名
    data/dictionaries/relations.csv  关系

用法::

    python scripts/exportCbdb.py
    python scripts/exportCbdb.py --db data/raw/cbdb_20261114.sqlite3 --out data/dictionaries
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

DYNASTY_MAP = {6: "唐", 15: "宋", 19: "明"}

# CBDB 的别名类型编码 -> 项目用词
ALIAS_TYPE = {
    4: "字", 5: "号", 6: "谥号", 3: "别名", 9: "小名",
    10: "小字", 11: "赐号", 14: "庙号", 15: "尊号",
}

# 亲疏关系按描述里的关键词归并到六类。CBDB 有几百种细分,这里只取能明确归类的。
RELATION_RULES = [
    ("君臣", ("恩主", "君主", "為Y之臣", "臣", "仕")),
    ("师生", ("師", "學", "授業", "弟子", "門人")),
    ("朋友", ("友",)),
    ("合作", ("推薦", "同", "共", "聯", "盟", "助")),
    ("对立", ("攻", "彈劾", "反對", "敵", "貶")),
]


def classify(desc: str) -> str:
    for label, keywords in RELATION_RULES:
        if any(k in desc for k in keywords):
            return label
    return ""


def reversed_direction(desc: str) -> bool:
    """CBDB 的成对关系里有「被 Y 推荐」这类反向写法,主体客体要交换。"""
    return desc.startswith("被") or desc.startswith("遭") or desc.startswith("為Y")


def export(db: Path, out: Path) -> None:
    con = sqlite3.connect(db)
    cur = con.cursor()
    out.mkdir(parents=True, exist_ok=True)

    params = tuple(DYNASTY_MAP)
    cur.execute(f"""
        SELECT b.c_personid, b.c_name_chn, b.c_birthyear, b.c_deathyear,
               b.c_dy, b.c_female, b.c_index_addr_id, b.c_notes,
               a.c_name_chn
        FROM BIOG_MAIN b
        LEFT JOIN ADDR_CODES a ON b.c_index_addr_id = a.c_addr_id
        WHERE b.c_dy IN ({",".join("?" * len(params))})
          AND b.c_birthyear > 0 AND b.c_deathyear > 0
          AND b.c_deathyear >= b.c_birthyear
          AND b.c_name_chn IS NOT NULL AND b.c_name_chn <> ''
        ORDER BY b.c_dy, b.c_birthyear
    """, params)
    rows = cur.fetchall()
    keep = {r[0] for r in rows}
    print(f"人物 {len(rows):,} 人")

    # 别名:先取字与号填进主表,全部类型再单独进 alias.csv
    aliases: dict[int, dict[int, str]] = {}
    for pid, name, tcode in cur.execute(
            "SELECT c_personid, c_alt_name_chn, c_alt_name_type_code FROM ALTNAME_DATA"):
        if pid in keep and name:
            aliases.setdefault(pid, {}).setdefault(tcode, name)

    with (out / "person.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["person_id", "name", "courtesy_name", "pseudonym",
                    "birth_year", "death_year", "dynasty", "birthplace",
                    "occupation", "coverage"])
        for pid, name, by, dy, dyn_id, female, addr, notes, addr_chn in rows:
            amap = aliases.get(pid, {})
            w.writerow([pid, name, amap.get(4, ""), amap.get(5, ""),
                        by, dy, DYNASTY_MAP[dyn_id],
                        addr_chn or "", "", "full"])

    with (out / "alias.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["alias_name", "person_id", "alias_type"])
        count = 0
        for pid, amap in aliases.items():
            for tcode, aname in amap.items():
                w.writerow([aname, pid, ALIAS_TYPE.get(tcode, "其他")])
                count += 1
    print(f"别名 {count:,} 条")

    # 亲属关系全部归为家族
    relations: list[tuple] = []
    for pid, kid, src, pages in cur.execute(
            "SELECT c_personid, c_kin_id, c_source, c_pages FROM KIN_DATA"):
        if pid in keep and kid in keep:
            relations.append((pid, kid, "家族", "", "", f"CBDB:{src}:{pages}"))

    # 亲疏关系按关键词归并,认不出的丢弃
    sql = """
        SELECT a.c_personid, a.c_assoc_id, a.c_assoc_code,
               a.c_assoc_first_year, a.c_assoc_last_year, a.c_source, a.c_pages,
               c.c_assoc_desc_chn
        FROM ASSOC_DATA a
        LEFT JOIN ASSOC_CODES c ON a.c_assoc_code = c.c_assoc_code
    """
    dropped = 0
    for pid, aid, code, fy, ly, src, pages, desc in cur.execute(sql):
        if pid not in keep or aid not in keep:
            continue
        label = classify(desc or "")
        if not label:
            dropped += 1
            continue
        s, t = (aid, pid) if reversed_direction(desc or "") else (pid, aid)
        relations.append((s, t, label, fy or "", ly or "", f"CBDB:{src}:{pages}"))

    with (out / "relations.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_id", "target_id", "relation_type",
                    "start_year", "end_year", "evidence"])
        w.writerows(relations)
    print(f"关系 {len(relations):,} 条(未归类丢弃 {dropped:,} 条)")
    con.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path,
                   default=Path("data/raw/cbdb_20261114.sqlite3"))
    p.add_argument("--out", type=Path, default=Path("data/dictionaries"))
    args = p.parse_args()
    export(args.db, args.out)


if __name__ == "__main__":
    main()
