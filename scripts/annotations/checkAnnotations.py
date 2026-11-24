#!/usr/bin/env python3
"""标注交付前自检，对应 docs/annotationGuidelines.md 第四节：

1. 事件表 event_name+year 无重复
2. 参与者表 person_id 全部存在于 person.csv
3. 身份表覆盖人物无空缺（默认对照 person.csv 全部 374 人；分半提交时用
   --roster 限定范围，如 --roster .scratch/workload/first187.csv）
4. 测试集句子与弱标注结果无交集（文件不存在或为空时视为通过并注明）

用法：
    python scripts/annotations/checkAnnotations.py
    python scripts/annotations/checkAnnotations.py --roster .scratch/workload/first187.csv
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANN = ROOT / "data" / "annotations"


def load(name):
    p = ANN / name
    if not p.exists():
        return None
    return list(csv.DictReader(p.open(encoding="utf-8-sig")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--roster", type=Path, default=None,
                    help="身份表覆盖范围名单（默认 person.csv 全量）")
    args = ap.parse_args()

    persons = list(csv.DictReader((ROOT / "data/dictionaries/person.csv").open(encoding="utf-8-sig")))
    person_ids = {r["person_id"] for r in persons}
    ok = True

    # 1. 事件表 event_name+year 无重复
    ev = load("event.csv")
    if ev is None:
        print("[1] event.csv 不存在 —— FAIL")
        ok = False
    else:
        seen, dup = set(), set()
        for r in ev:
            key = (r["event_name"].strip(), r["year"].strip())
            if key in seen:
                dup.add(key)
            seen.add(key)
        if dup:
            print(f"[1] 事件表 event_name+year 重复 {len(dup)} 条: {sorted(dup)[:5]} —— FAIL")
            ok = False
        else:
            print(f"[1] 事件表 {len(ev)} 条，event_name+year 无重复 —— PASS")

    # 2. 参与者表 person_id 合法
    pa = load("eventParticipant.csv")
    if pa is None:
        print("[2] eventParticipant.csv 不存在 —— FAIL")
        ok = False
    else:
        bad = [r for r in pa if r["person_id"].strip() not in person_ids]
        if bad:
            print(f"[2] 参与者表 {len(bad)} 行 person_id 不在 person.csv: "
                  f"{[(r['event_name'], r['person_id']) for r in bad[:5]]} —— FAIL")
            ok = False
        else:
            print(f"[2] 参与者表 {len(pa)} 行，person_id 全部存在于 person.csv —— PASS")

    # 3. 身份表覆盖无空缺
    pc = load("personCategory.csv")
    if args.roster:
        scope = {r["person_id"] for r in csv.DictReader(args.roster.open(encoding="utf-8-sig"))}
        scope_name = f"名单 {args.roster.name}"
    else:
        scope = person_ids
        scope_name = "person.csv 全量"
    if pc is None:
        print("[3] personCategory.csv 不存在 —— FAIL")
        ok = False
    else:
        covered = {r["person_id"].strip() for r in pc}
        missing = sorted(scope - covered, key=int)
        # 表内也不得有 person.csv 之外的人
        extra = covered - person_ids
        if missing or extra:
            if missing:
                print(f"[3] 身份表覆盖 {len(covered & scope)}/{len(scope)}（{scope_name}），"
                      f"缺 {len(missing)} 人: {missing[:10]} —— FAIL")
            if extra:
                print(f"[3] 身份表含 person.csv 之外的人: {sorted(extra)[:10]} —— FAIL")
            ok = False
        else:
            empty_cat = [r for r in pc if not r["category_name"].strip()]
            if empty_cat:
                print(f"[3] 身份表有 {len(empty_cat)} 行 category_name 为空 —— FAIL")
                ok = False
            else:
                print(f"[3] 身份表覆盖 {len(scope)}/{len(scope)}（{scope_name}），无空缺 —— PASS")

    # 4. 测试集与弱标注隔离
    ts = load("testSet.csv")
    weak = None
    for name in ("weakLabels.csv", "weak_labels.csv"):
        weak = load(name)
        if weak is not None:
            break
    if not ts or not weak:
        print("[4] 测试集或弱标注结果尚不存在/为空，无交集可查 —— PASS（待 C 阶段复验）")
    else:
        ts_sents = {r["sentence"].strip() for r in ts}
        wkey = "sentence" if "sentence" in weak[0] else list(weak[0].keys())[1]
        weak_sents = {r[wkey].strip() for r in weak}
        inter = ts_sents & weak_sents
        if inter:
            print(f"[4] 测试集与弱标注有 {len(inter)} 句交集 —— FAIL")
            ok = False
        else:
            print(f"[4] 测试集 {len(ts_sents)} 句与弱标注 {len(weak_sents)} 条无交集 —— PASS")

    print("总体:", "全部通过" if ok else "存在未通过项")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
