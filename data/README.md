# 数据目录

| 目录 | 用途 |
|---|---|
| raw/ | 原始古籍文本，不入库 |
| processed/ | 清洗后文本 |
| dictionaries/ | 人物表与别名表 |
| samples/ | 标注样本与测试集 |

原始语料体积较大，已在 .gitignore 中排除，只保留目录。

## 当前数据

由 `scripts/exportCbdb.py` 从 CBDB 离线库导出。筛选条件：唐、宋、明三朝，生卒年齐全，且至少有一条关系。

| 文件 | 内容 | 规模 |
|---|---|---|
| dictionaries/person.csv | 人物 | 5,077 人 |
| dictionaries/alias.csv | 别名 | 7,033 条 |
| dictionaries/relations.csv | 关系 | 11,949 条 |

朝代分布：唐 1,321、宋 2,948、明 808。有别名的人物占 78.4%，度数不小于 5 的有 1,240 人，最大度数 339。
关系两端均在人物表内，无孤立节点。
