# 脚本目录

按用途分子目录，每个脚本自己写日志到 `logs/`。

```
scripts/
└── dataPrep/          数据准备与导出
    └── exportCbdb.py  从 CBDB 离线库导出人物/别名/关系三张表
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
