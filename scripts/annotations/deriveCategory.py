#!/usr/bin/env python3
"""由 CBDB 官职记录按规则推导人物身份（宰相/将领/政治家），推不出的交给人工表兜底。

用法：
    python scripts/annotations/deriveCategory.py                 # 全部 374 人
    python scripts/annotations/deriveCategory.py --roster .scratch/workload/first187.csv

输入：
    data/dictionaries/person.csv         人物表
    data/dictionaries/personOffice.csv   CBDB 官职记录
    scripts/annotations/categoryRules.csv    规则表（官职名子串 → 身份）
    scripts/annotations/manualCategory.csv   人工标注（rule 推不出的身份）
输出：
    data/annotations/personCategory.csv  （按 person_id 排序；--roster 时只含名单内人物）

规范见 docs/annotationGuidelines.md：宰相必兼标政治家；每人至少一条，推不出写「其他」。
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALID = {"政治家", "军事家", "文学家", "诗人", "思想家", "史学家", "书法家", "宰相", "将领", "其他"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--roster", type=Path, default=None, help="只处理名单内 person_id")
    args = ap.parse_args()

    persons = list(csv.DictReader((ROOT / "data/dictionaries/person.csv").open(encoding="utf-8-sig")))
    persons.sort(key=lambda r: int(r["person_id"]))
    if args.roster:
        keep = {r["person_id"] for r in csv.DictReader(args.roster.open(encoding="utf-8-sig"))}
        persons = [p for p in persons if p["person_id"] in keep]

    offices = {}
    for r in csv.DictReader((ROOT / "data/dictionaries/personOffice.csv").open(encoding="utf-8-sig")):
        offices.setdefault(r["person_id"], []).append(r["office_name"])

    rules = list(csv.DictReader((ROOT / "scripts/annotations/categoryRules.csv").open(encoding="utf-8-sig")))

    manual = {}
    mpath = ROOT / "scripts/annotations/manualCategory.csv"
    if mpath.exists():
        for r in csv.DictReader(mpath.open(encoding="utf-8-sig")):
            assert r["category_name"] in VALID, f"非法身份: {r}"
            manual.setdefault(r["person_id"], []).append((r["category_name"], r.get("evidence", "")))

    rows = []
    n_rule = n_manual = n_other = 0
    for p in persons:
        pid = p["person_id"]
        matched = {}  # category -> set(evidence offices)
        for off in offices.get(pid, []):
            for rule in rules:
                if rule.get("dynasty") and rule["dynasty"] != p["dynasty"]:
                    continue  # 朝代限定规则（如「大学士」仅明代指宰相）
                if rule["pattern"] in off:
                    # 将领规则排除参谋/参议/参赞类幕职（如吕祖谦任宣抚司参谋官，不算将领）
                    if rule["category_name"] == "将领" and any(m in off for m in ("参谋", "参议", "参赞")):
                        continue
                    matched.setdefault(rule["category_name"], set()).add(off)
        if "宰相" in matched and "政治家" not in matched:
            matched["政治家"] = set()  # 拜相者必兼标政治家，evidence 沿用宰相官职
            matched["政治家"] = matched["宰相"] | set()
        out = []
        for cat in ("宰相", "将领", "政治家"):
            if cat in matched:
                out.append({"person_id": pid, "name": p["name"], "category_name": cat,
                            "source": "rule", "confidence": "0.9",
                            "evidence": "/".join(sorted(matched[cat]))})
                n_rule += 1
        if not out and not manual.get(pid):
            out.append({"person_id": pid, "name": p["name"], "category_name": "其他",
                        "source": "rule", "confidence": "1.0",
                        "evidence": "CBDB 无官职记录" if pid not in offices else "官职记录无法推出身份"})
            n_other += 1
        have_cat = {r["category_name"] for r in out}
        for cat, ev in manual.get(pid, []):
            if cat not in have_cat:
                out.append({"person_id": pid, "name": p["name"], "category_name": cat,
                            "source": "manual", "confidence": "1.0", "evidence": ev})
                n_manual += 1
        if not out:  # 双保险：manual 存在时上面已跳过其他
            out.append({"person_id": pid, "name": p["name"], "category_name": "其他",
                        "source": "rule", "confidence": "1.0", "evidence": "官职记录无法推出身份"})
        rows.extend(out)

    target = ROOT / "data/annotations/personCategory.csv"
    with target.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["person_id", "name", "category_name", "source", "confidence", "evidence"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(persons)} 人 → {len(rows)} 行（rule {n_rule} / manual {n_manual} / 其他 {n_other}）→ {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
