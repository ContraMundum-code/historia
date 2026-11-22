# 数据目录

| 目录 | 用途 |
|---|---|
| raw/ | 原始古籍文本，不入库 |
| processed/ | 清洗后文本 |
| dictionaries/ | 人物表与别名表 |
| corpus/ | 按人切好的本传正文，入库 |
| samples/ | 标注样本与测试集 |

原始语料体积较大，已在 .gitignore 中排除，只保留目录。

## 当前数据

由 `scripts/dataPrep/exportCbdb.py` 从 CBDB 离线库导出。原始库保留在 `data/raw/`，
三张 CSV 每次重跑覆盖，不保留中间版本。

筛选链：唐宋明三朝 → 生卒年齐全 → 至少一条关系 → 按朝代配额抽样（唐 120、宋 200、明 100）
→ 只保留样本内部的关系。抽样按字段齐全度、别名数、关系度数排序。

| 文件 | 内容 | 规模 |
|---|---|---|
| dictionaries/person.csv | 人物 | 374 人 |
| dictionaries/alias.csv | 别名 | 1,124 条 |
| dictionaries/relations.csv | 关系 | 1,426 条 |

朝代分布：宋 190、唐 92、明 92。字段齐全度：字 97%、号 64%、籍贯 99%、生卒 100%。
平均度数 7.6，度数不小于 10 的有 86 人。关系类型：师生 450、家族 331、合作 261、朋友 264、对立 100、君臣 20。

## corpus/ 本传正文

由 `scripts/corpus/02_extractBiographies.py` 从维基文库的宋史、明史、舊唐書、新唐書中
按人抽出，每人一个 `{person_id}_{姓名}.txt`，命名与 `dictionaries/person.csv` 的
`person_id` 对齐。`manifest.csv` 记录书名、卷次、匹配方式、字数与状态。

personA 段（前 125 人）的覆盖：唐 6/6、宋 106/118、明 1/1，合计 113 人（90.4%），正文中位 2,262 字，
合计 32.2 万字。未命中的 12 人在 `manifest.csv` 中标 `status=missing`，这 12 人在宋史中
只有零散提及、没有本传，需另找文集或方志。

personB 段（中间 125 人，person_id 10289–32540）：唐 35/39、宋 52/70、明 15/16，合计 102 人（81.6%），
约 30.7 万字；另含 9 位唐帝本纪（reign 模式）。23 名未命中者逐人核查了四部正史全文与标题，
并尝试维基文库《宋元學案》《唐才子傳》《宋史翼》及 ctext 检索，均无本传，逐人原因见
`corpus/missing.csv`；文献登记（书名/作者/朝代/类型/链接）见 `corpus/document_registry.csv`。

两段合计：已采 215 人，62.9 万字，覆盖 250 人名单的 86%。

注：personB 段底本改用 wikitext 批量抓取 + 本地模板展开（脚本在 .scratch，未入库），
内容与 01_fetchSources.py 的渲染纯文本等价；过程中给 02_extractBiographies.py 的
异体表补充了 翱→翺、栖→棲 两条映射。
