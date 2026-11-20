# 脚本目录

按用途分子目录，每个脚本自己写日志到 `logs/`。

```
scripts/
├── dataPrep/                    数据准备与导出
│   └── exportCbdb.py            从 CBDB 离线库导出人物/别名/关系三张表
└── corpus/                      古籍底本采集
    ├── 01_fetchSources.py       从维基文库拉取纪传体正史全文
    └── 02_extractBiographies.py 按人抽出本传正文
```

## 约定

1. 脚本路径相对仓库根解析，不依赖当前工作目录。
2. 每个脚本向 `logs/<脚本名>_<时间戳>.log` 写全过程日志，`logs/` 不入库。
3. 关键步骤打检查点，结束时对账；不变量不成立直接抛错退出。
4. 一次性探索脚本放 `/tmp`，不进仓库。

## exportCbdb.py

```bash
python scripts/dataPrep/exportCbdb.py
```

输入 `data/raw/cbdb_20261114.sqlite3`，输出到 `data/dictionaries/`。

筛选条件：唐宋明三朝、生卒年齐全、至少有一条关系。

## corpus/01_fetchSources.py

```bash
python scripts/corpus/01_fetchSources.py
python scripts/corpus/01_fetchSources.py --books 宋史 --force
```

从中文维基文库 MediaWiki API 拉取宋史、明史、舊唐書、新唐書全部正卷，按卷缓存到
`.scratch/sources/<书名>.json`。命中缓存时跳过，`--force` 强制重下。

四部合计 1,293 卷、约 90 MB，6 并发约 3 分钟。只收 `卷N` 正卷页面，排除
「(四庫全書本)」「全覽」「紀事本末」等同前缀页面。

## corpus/02_extractBiographies.py

```bash
python scripts/corpus/02_extractBiographies.py
python scripts/corpus/02_extractBiographies.py --roster .scratch/workload/personA.csv
```

读取名单与底本缓存，按人物名定位列传条目，输出到 `data/corpus/`：每人一个
`{person_id}_{姓名}.txt`，外加 `manifest.csv` 记录书名、卷次、匹配方式与字数。

定位规则：列传卷以人名为标题分节，标题清洗后即索引；标题失配时退回
「人名，字某某」正文特征串。清洗涵盖繁简转换标记、内链、帝号括注、附传前缀，
并统一异体字（脩→修、褘→禕）。

当前对 125 人名单的覆盖率 102 人（81.6%），唐 6/6、宋 95/118、明 1/1，正文中位 2,336 字。
未命中名单见 `data/corpus/manifest.csv` 的 `status=missing` 行。
