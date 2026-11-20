# 数据目录

| 目录 | 用途 |
|---|---|
| raw/ | 原始古籍文本，不入库 |
| processed/ | 清洗后文本 |
| dictionaries/ | 人物表与别名表 |
| samples/ | 标注样本与测试集 |

原始语料体积较大，已在 .gitignore 中排除，只保留目录。

## 当前数据

由 `scripts/exportCbdb.py` 从 CBDB 离线库导出，只保留唐、宋、明三朝且生卒年齐全的人物。

| 文件 | 内容 | 规模 |
|---|---|---|
| dictionaries/person.csv | 人物 | 14,740 人 |
| dictionaries/alias.csv | 别名 | 19,158 条 |
| dictionaries/relations.csv | 关系 | 11,949 条 |

其中 5,077 人至少有一条关系，1,240 人度数不小于 5。核心人物建议从这 5,077 人里按度数挑选。
