# 脚本目录

数据准备期的一次性工具，用于把外部数据源加工成 `data/` 下的交付文件。

**这些脚本不参与系统运行**。Flask 后端启动、前端构建、数据库读写都不依赖本目录；
最终交付的系统只需 `backend/`、`frontend/`、`database/`、`data/`、`docs/`。本目录保留
在仓库里是为了让数据处理过程可复现，`docs/zhangcheng/system_design.md` 的目录结构图不列此项。

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

从中文维基文库 MediaWiki API 拉取宋史、明史、旧唐书、新唐书全部正卷，按卷缓存到
`.scratch/sources/<书名>.json`。已缓存的卷跳过，`--force` 强制重下。

取渲染后的纯文本（`prop=extracts&explaintext`）而非 wikitext：文库正文里人名用
`{{ProperNoun|司马光}}` 包、年号用 `{{YL|元丰三年}}` 包、生僻字用 `{{SKchar|2593}}`
编码，直接剥模板会丢姓名和年号，渲染文本已展开成原字。

四部合计 1,293 卷、约 86 MB，3 并发约 10 分钟。只收 `卷N` 正卷页面，排除
「(四库全书本)」「全览」「纪事本末」等同前缀页面。表格卷（宰辅表、宗室世系表、
诸王世表）渲染超时，取不到的记入 `<书名>.missing.json`，共 32 卷，均不含列传正文。

## corpus/02_extractBiographies.py

```bash
python scripts/corpus/02_extractBiographies.py
python scripts/corpus/02_extractBiographies.py --roster .scratch/workload/personA.csv
```

读取名单与底本缓存，按人物名定位列传条目，输出到 `data/corpus/`：每人一个
`{person_id}_{姓名}.txt`，外加 `manifest.csv` 记录书名、卷次、匹配方式与字数。

定位规则按优先级依次尝试：

1. 正名标题：列传卷以人名为标题分节，标题清洗（繁简标记、内链、帝号括注）后即索引
2. 附传标题：`弟 肇`、`从孙 祖禹`、`太祖弟 魏悼王 廷美` 这类只写名不写姓的标题，
   取末词并用父级标题姓氏补全，父级姓氏与名单姓氏一致才采纳
3. 帝王本纪：不以姓名立目，用「皇帝，讳某」定位，返回整卷
4. 正文特征串：「人名，字某某」兜底

另统一异体字：修→修、濬→浚、叡→睿、袆→祎、沉→沈、眘→昚、勗→勖。

当前对 125 人名单的覆盖率 125 人（100%），唐 6/6、宋 118/118、明 1/1，正文中位 1,988 字。

`data/corpus/sourcesManual.csv` 登记手工补录的传记（person_id、出处、待复核说明）。
脚本重跑时保留这些文件，既不删除也不覆写题头；名单里既无自动结果、又无手工文件的记
`status=missing`。手工文件的题头固定为 `【出处】` 与 `【存疑】` 两行，统计字数时整行剔除。
