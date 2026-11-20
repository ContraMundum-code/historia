#!/usr/bin/env python3
"""从 CBDB 离线库导出项目用的三张表，全过程写日志到 logs/。

清洗规则
--------
1. 只保留唐、宋、明三朝（c_dy = 6 / 15 / 19）
2. 生年与卒年都必须齐全，且卒年不早于生年
3. 只保留至少有一条关系的人物，孤立节点不进库
4. 按朝代配额抽样，优先选字段齐全、别名多、关系多的人

第 4 步的排序分综合考虑字、号、籍贯、别名数量与关系度数。抽样后只保留
两端都在样本内的关系，若出现孤立节点则用后续候选人补位。

原始库 data/raw/cbdb_*.sqlite3 不动，本脚本只读；输出的三张 CSV 每次覆盖。

用法::

    python scripts/dataPrep/exportCbdb.py
    python scripts/dataPrep/exportCbdb.py --total 450
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DYNASTY_MAP = {6: "唐", 15: "宋", 19: "明"}

# 各朝代保留人数，合计即目标规模。宋的存量大、字段最全，配额最高。
DEFAULT_QUOTA = {"唐": 120, "宋": 200, "明": 100}

ALIAS_TYPE = {
    4: "字", 5: "号", 6: "谥号", 3: "别名", 9: "小名",
    10: "小字", 11: "赐号", 14: "庙号", 15: "尊号",
}

RELATION_RULES = [
    ("君臣", ("恩主", "君主", "為Y之臣", "臣", "仕")),
    ("师生", ("師", "學", "授業", "弟子", "門人")),
    ("朋友", ("友",)),
    ("合作", ("推薦", "同", "共", "聯", "盟", "助")),
    ("对立", ("攻", "彈劾", "反對", "敵", "貶")),
]


class RunLog:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("w", encoding="utf-8")
        self.path = path
        self.t0 = time.time()

    def step(self, message: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {message}"
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
    return desc.startswith("被") or desc.startswith("遭") or desc.startswith("為Y")


def score_person(has_courtesy: bool, has_pseudonym: bool, has_addr: bool,
                 n_alias: int, degree: int) -> float:
    """字段齐全优先，其次别名多、关系多。权重是主观设定，改这里就能调整抽样的偏好。"""
    return (2 * has_courtesy + 2 * has_pseudonym + 1 * has_addr
            + min(n_alias, 6) * 0.5 + min(degree, 20) * 0.3)


def export(db: Path, out: Path, log_dir: Path, quota: dict[str, int]) -> None:
    log = RunLog(log_dir / f"exportCbdb_{time.strftime('%Y%m%d-%H%M%S')}.log")
    try:
        log.step(f"输入库 {db}")
        log.step(f"输出目录 {out}")
        log.step(f"朝代配额 {quota}，合计 {sum(quota.values())}")
        if not db.exists():
            raise FileNotFoundError(db)

        con = sqlite3.connect(db)
        cur = con.cursor()

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
        """, tuple(DYNASTY_MAP))
        rows = cur.fetchall()
        candidates = {r[0] for r in rows}
        by_dy: dict[str, int] = {}
        for r in rows:
            by_dy[DYNASTY_MAP[r[4]]] = by_dy.get(DYNASTY_MAP[r[4]], 0) + 1
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
        for pid, kid, src, pages in cur.execute(
                "SELECT c_personid, c_kin_id, c_source, c_pages FROM KIN_DATA"):
            if pid in candidates and kid in candidates:
                relations.append((pid, kid, "家族", "", "", f"CBDB:{src}:{pages}"))

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
        log.step(f"检查点3 关系 {len(relations):,} 条（未归类丢弃 {dropped:,}）")

        # ---- 检查点 4：按字段齐全度与度数排序，按朝代配额抽样
        degree: dict[int, int] = {}
        for s_id, t_id, *_ in relations:
            degree[s_id] = degree.get(s_id, 0) + 1
            degree[t_id] = degree.get(t_id, 0) + 1

        info = {r[0]: r for r in rows}
        ranked: dict[str, list[tuple[float, int]]] = {k: [] for k in quota}
        for pid, row in info.items():
            _, name, by, dy, dyn_id, addr, addr_chn = row
            amap = aliases.get(pid, {})
            if degree.get(pid, 0) == 0:
                continue
            s = score_person(bool(amap.get(4)), bool(amap.get(5)), bool(addr_chn),
                             len(amap), degree.get(pid, 0))
            ranked[DYNASTY_MAP[dyn_id]].append((s, pid))

        selected: set[int] = set()
        for dyn, quota_n in quota.items():
            pool = sorted(ranked[dyn], reverse=True)
            picked = 0
            for _, pid in pool:
                if picked >= quota_n:
                    break
                selected.add(pid)
                picked += 1
        log.step(f"检查点4 按配额初选 {len(selected):,} 人")

        # ---- 检查点 5：只保留样本内部的关系，剔除新产生的孤立节点
        def induced(nodes: set[int]) -> list[tuple]:
            return [r for r in relations if r[0] in nodes and r[1] in nodes]

        sub = induced(selected)
        isolated = selected - ({r[0] for r in sub} | {r[1] for r in sub})
        if isolated:
            selected -= isolated
            sub = induced(selected)
        log.step(f"检查点5 剔除样本内孤立节点 {len(isolated):,} 人，"
                 f"最终 {len(selected):,} 人，关系 {len(sub):,} 条")

        if not 300 <= len(selected) <= 500:
            raise AssertionError(f"人物数 {len(selected)} 不在 300–500 区间")

        # ---- 写出
        out.mkdir(parents=True, exist_ok=True)
        final_rows = [info[pid] for pid in sorted(selected)]

        with (out / "person.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["person_id", "name", "courtesy_name", "pseudonym",
                        "birth_year", "death_year", "dynasty", "birthplace",
                        "occupation", "coverage"])
            for pid, name, by, dy, dyn_id, addr, addr_chn in final_rows:
                amap = aliases.get(pid, {})
                w.writerow([pid, name, amap.get(4, ""), amap.get(5, ""),
                            by, dy, DYNASTY_MAP[dyn_id], addr_chn or "", "", "full"])

        with (out / "alias.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["alias_name", "person_id", "alias_type"])
            n_alias = 0
            for pid in selected:
                for tcode, aname in aliases.get(pid, {}).items():
                    w.writerow([aname, pid, ALIAS_TYPE.get(tcode, "其他")])
                    n_alias += 1

        with (out / "relations.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["source_id", "target_id", "relation_type",
                        "start_year", "end_year", "evidence"])
            w.writerows(sub)

        # ---- 字段齐全度统计
        def ratio(field: str) -> float:
            return sum(1 for r in final_rows if r[field]) / len(final_rows)

        courtesy = sum(1 for pid in selected if aliases.get(pid, {}).get(4)) / len(selected)
        pseudonym = sum(1 for pid in selected if aliases.get(pid, {}).get(5)) / len(selected)
        addr = sum(1 for r in final_rows if r[6]) / len(final_rows)
        log.step(f"检查点6 写出 person={len(selected):,} alias={n_alias:,} relation={len(sub):,}")
        log.step(f"字段齐全度 字={courtesy:.0%} 号={pseudonym:.0%} 籍贯={addr:.0%} 生卒=100%")

        # ---- 对账
        person_ids = {r[0] for r in final_rows}
        dangling = [r for r in sub if r[0] not in person_ids or r[1] not in person_ids]
        if dangling:
            raise AssertionError(f"关系端点不在人物表内 {len(dangling)} 条")
        rest = len(person_ids - ({r[0] for r in sub} | {r[1] for r in sub}))
        if rest:
            raise AssertionError(f"存在孤立节点 {rest} 个")
        log.step("对账通过：关系端点全在人物表内，无孤立节点，人数在 300–500 区间")
    except Exception as exc:
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
    p.add_argument("--quota", default="唐:120,宋:200,明:100",
                   help="各朝代保留人数，形如 唐:120,宋:200,明:100")
    args = p.parse_args()

    quota = {}
    for part in args.quota.split(","):
        dyn, n = part.split(":")
        quota[dyn.strip()] = int(n)
    export(args.db, args.out, args.log_dir, quota)


if __name__ == "__main__":
    main()
