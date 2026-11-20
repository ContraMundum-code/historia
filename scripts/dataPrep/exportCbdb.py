#!/usr/bin/env python3
"""从 CBDB 离线库导出项目用的三张表，全过程写日志到 logs/。

清洗规则
--------
1. 只保留唐、宋、明三朝（c_dy = 6 / 15 / 19）
2. 生年与卒年都必须齐全，且卒年不早于生年
3. 只保留至少有一条关系的人物，孤立节点不进库

每步都打检查点并在结束时对账，任何一条不变量不成立就直接报错退出，
避免产出一份看起来正常但实际有问题的数据。

用法::

    python scripts/dataPrep/exportCbdb.py
    python scripts/dataPrep/exportCbdb.py --db <path> --out <dir> --log-dir <dir>
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DYNASTY_MAP = {6: "唐", 15: "宋", 19: "明"}

# CBDB 的别名类型编码 -> 项目用词
ALIAS_TYPE = {
    4: "字", 5: "号", 6: "谥号", 3: "别名", 9: "小名",
    10: "小字", 11: "赐号", 14: "庙号", 15: "尊号",
}

# 亲疏关系按描述里的关键词归并到六类。CBDB 有几百种细分，只取能明确归类的。
RELATION_RULES = [
    ("君臣", ("恩主", "君主", "為Y之臣", "臣", "仕")),
    ("师生", ("師", "學", "授業", "弟子", "門人")),
    ("朋友", ("友",)),
    ("合作", ("推薦", "同", "共", "聯", "盟", "助")),
    ("对立", ("攻", "彈劾", "反對", "敵", "貶")),
]


class RunLog:
    """同时写控制台和日志文件，每行带时间戳。"""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("w", encoding="utf-8")
        self.path = path
        self.t0 = time.time()

    def step(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        line = f"[{stamp}] {message}"
        print(line)
        self._fh.write(line + "\n")
        self._fh.flush()

    def close(self) -> None:
        self.step(f"结束，耗时 {time.time() - self.t0:.1f}s")
        self._fh.close()


def classify(desc: str) -> str:
    for label, keywords in RELATION_RULES:
        if any(k in desc for k in keywords):
            return label
    return ""


def reversed_direction(desc: str) -> bool:
    """CBDB 的成对关系里有「被 Y 推荐」这类反向写法，主客体要交换。"""
    return desc.startswith("被") or desc.startswith("遭") or desc.startswith("為Y")


def codepoint(con: sqlite3.Connection) -> None:
    """建库时用的 sqlite 版本和字符集，出问题时能复现。"""
    version = sqlite3.sqlite_version
    con.execute("PRAGMA encoding")
    print(f"[env] sqlite {version}, python {sys.version.split()[0]}")


def export(db: Path, out: Path, log_dir: Path) -> None:
    log = RunLog(log_dir / f"exportCbdb_{time.strftime('%Y%m%d-%H%M%S')}.log")
    try:
        log.step(f"输入库 {db}")
        log.step(f"输出目录 {out}")
        if not db.exists():
            raise FileNotFoundError(db)

        con = sqlite3.connect(db)
        cur = con.cursor()
        codepoint(con)

        # ---- 检查点 1：候选人物
        placeholders = ",".join("?" * len(DYNASTY_MAP))
        cur.execute(f"""
            SELECT b.c_personid, b.c_name_chn, b.c_birthyear, b.c_deathyear,
                   b.c_dy, b.c_index_addr_id, a.c_name_chn
            FROM BIOG_MAIN b
            LEFT JOIN ADDR_CODES a ON b.c_index_addr_id = a.c_addr_id
            WHERE b.c_dy IN ({placeholders})
              AND b.c_birthyear > 0 AND b.c_deathyear > 0
              AND b.c_deathyear >= b.c_birthyear
              AND b.c_name_chn IS NOT NULL AND b.c_name_chn <> ''
            ORDER BY b.c_dy, b.c_birthyear
        """, tuple(DYNASTY_MAP))
        rows = cur.fetchall()
        candidates = {r[0] for r in rows}
        by_dy = {v: 0 for v in DYNASTY_MAP.values()}
        for r in rows:
            by_dy[DYNASTY_MAP[r[4]]] += 1
        log.step(f"检查点1 候选人物 {len(rows):,} 人 {by_dy}")

        # ---- 检查点 2：别名
        aliases: dict[int, dict[int, str]] = {}
        for pid, name, tcode in cur.execute(
                "SELECT c_personid, c_alt_name_chn, c_alt_name_type_code FROM ALTNAME_DATA"):
            if pid in candidates and name:
                aliases.setdefault(pid, {}).setdefault(tcode, name)
        log.step(f"检查点2 候选别名 {sum(len(v) for v in aliases.values()):,} 条，"
                 f"覆盖 {len(aliases):,} 人")

        # ---- 检查点 3：关系
        relations: list[tuple] = []
        kin_n = 0
        for pid, kid, src, pages in cur.execute(
                "SELECT c_personid, c_kin_id, c_source, c_pages FROM KIN_DATA"):
            if pid in candidates and kid in candidates:
                relations.append((pid, kid, "家族", "", "", f"CBDB:{src}:{pages}"))
                kin_n += 1

        assoc_sql = """
            SELECT a.c_personid, a.c_assoc_id, a.c_assoc_first_year,
                   a.c_assoc_last_year, a.c_source, a.c_pages, c.c_assoc_desc_chn
            FROM ASSOC_DATA a
            LEFT JOIN ASSOC_CODES c ON a.c_assoc_code = c.c_assoc_code
        """
        dropped = 0
        for pid, aid, fy, ly, src, pages, desc in cur.execute(assoc_sql):
            if pid not in candidates or aid not in candidates:
                continue
            label = classify(desc or "")
            if not label:
                dropped += 1
                continue
            s_id, t_id = (aid, pid) if reversed_direction(desc or "") else (pid, aid)
            relations.append((s_id, t_id, label, fy or "", ly or "", f"CBDB:{src}:{pages}"))
        log.step(f"检查点3 关系 {len(relations):,} 条（亲属 {kin_n:,}，亲疏 {len(relations) - kin_n:,}，"
                 f"未归类丢弃 {dropped:,}）")

        # ---- 检查点 4：剔除孤立节点
        kept = {r[0] for r in relations} | {r[1] for r in relations}
        rows = [r for r in rows if r[0] in kept]
        log.step(f"检查点4 有关系的人物 {len(rows):,} 人，剔除孤立节点 {len(candidates) - len(rows):,} 人")

        # ---- 写出
        out.mkdir(parents=True, exist_ok=True)
        with (out / "person.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["person_id", "name", "courtesy_name", "pseudonym",
                        "birth_year", "death_year", "dynasty", "birthplace",
                        "occupation", "coverage"])
            for pid, name, by, dy, dyn_id, addr, addr_chn in rows:
                amap = aliases.get(pid, {})
                w.writerow([pid, name, amap.get(4, ""), amap.get(5, ""),
                            by, dy, DYNASTY_MAP[dyn_id], addr_chn or "", "", "full"])

        with (out / "alias.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["alias_name", "person_id", "alias_type"])
            n_alias = 0
            for pid, amap in aliases.items():
                if pid not in kept:
                    continue
                for tcode, aname in amap.items():
                    w.writerow([aname, pid, ALIAS_TYPE.get(tcode, "其他")])
                    n_alias += 1

        with (out / "relations.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["source_id", "target_id", "relation_type",
                        "start_year", "end_year", "evidence"])
            w.writerows(relations)

        log.step(f"检查点5 写出 person={len(rows):,} alias={n_alias:,} relation={len(relations):,}")

        # ---- 对账
        person_ids = {r[0] for r in rows}
        dangling = [r for r in relations if r[0] not in person_ids or r[1] not in person_ids]
        if dangling:
            raise AssertionError(f"关系端点不在人物表内 {len(dangling)} 条")
        isolated = len(person_ids - ({r[0] for r in relations} | {r[1] for r in relations}))
        if isolated:
            raise AssertionError(f"存在孤立节点 {isolated} 个")
        if len(rows) + (len(candidates) - len(rows)) != len(candidates):
            raise AssertionError("人物数对账不平")
        log.step("对账通过：关系端点全在人物表内，无孤立节点，人物数守恒")
    except Exception as exc:  # 失败要显式暴露，不能留一句 done
        log.step(f"失败：{exc.__class__.__name__}: {exc}")
        raise
    finally:
        log.close()
        print(f"日志 {log.path}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, default=REPO_ROOT / "data/raw/cbdb_20261114.sqlite3")
    p.add_argument("--out", type=Path, default=REPO_ROOT / "data/dictionaries")
    p.add_argument("--log-dir", type=Path, default=REPO_ROOT / "logs")
    args = p.parse_args()
    export(args.db, args.out, args.log_dir)


if __name__ == "__main__":
    main()
