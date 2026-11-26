# B 阶段前半段交付记录

胡豪负责 `person.csv` 按 `person_id` 升序排列后的前 187 人（13–16504）。
本目录暂无他自撰的说明文档，以下内容以主分支的实际数据为准，来源为 PR #3。

## 交付内容

| 文件 | 内容 | 规模 |
|---|---|---|
| `data/annotations/personCategory.csv` | 前 187 人身份 | 345 条，187 人每人至少一条，「其他」11 条 |
| `data/annotations/event.csv` | 历史事件 | 54 条 |
| `data/annotations/eventParticipant.csv` | 事件参与者 | 74 条 |
| `scripts/annotations/deriveCategory.py` | 按官职推身份 | 规则见 `categoryRules.csv` |
| `scripts/annotations/categoryRules.csv` | 官职到身份的映射规则 | 64 条 |
| `scripts/annotations/manualCategory.csv` | 规则推不出时的人工判断 | 65 条 |
| `scripts/annotations/checkAnnotations.py` | 标注自检 | 五项，见 `../zhangcheng/annotationGuidelines.md` |

同目录不设其他成员的文件。事件按 `event_name + year` 去重，参与者 `person_id` 必须存在于
`data/dictionaries/person.csv`。

## 已知问题

6 条事件原先没有指定主角，2026-11-26 已按「事件名所指的叙事焦点」补齐，59 条事件现各有一名主角。

关系类型、身份词表等跨成员约定以 `../zhangcheng/annotationGuidelines.md` 为准，本目录不另立规则。
