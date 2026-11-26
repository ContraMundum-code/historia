# Historia：中国历史人物文本挖掘与知识分析系统

从古籍中识别人物、抽取人物关系，构建跨朝代人物关系图谱。

当前覆盖唐、宋、明三朝，374 位人物，1,426 条人物关系。

## 目录

```
historia/
├── frontend/            Vue 3 前端
│   └── src/
│       ├── api/         接口封装
│       ├── views/       页面
│       └── router/      路由
├── backend/             Flask 后端
│   ├── app/
│   │   ├── models/      ORM 模型
│   │   ├── routes/      接口路由
│   │   ├── services/    业务逻辑
│   │   └── nlp/         文本抽取模块
│   ├── migrations/      数据库迁移
│   └── run.py           开发入口
├── data/
│   ├── raw/             CBDB 离线库（不入库）
│   ├── corpus/          330 篇本传正文与采集登记表
│   ├── dictionaries/    人物、别名、关系、官职四张表
│   └── annotations/     事件、参与者、身份、测试集四张标注表
├── database/            建表与初始化脚本
├── scripts/
│   ├── dataPrep/        CBDB 导出
│   └── corpus/          语料采集与抽取（一次性工具）
├── docs/                设计与接口文档
└── logs/                脚本运行日志（不入库）
```

## 数据现状

| 文件 | 内容 | 规模 |
|---|---|---|
| `data/dictionaries/person.csv` | 人物 | 374 人 |
| `data/dictionaries/alias.csv` | 别名 | 1,124 条 |
| `data/dictionaries/relations.csv` | 关系 | 1,426 条 |
| `data/raw/cbdb_20261114.sqlite3` | CBDB 离线库 | 561 MB |

数据由 `scripts/dataPrep/exportCbdb.py` 从 CBDB 导出，筛选唐宋明三朝、生卒年齐全、
至少有一条关系的人物，按朝代配额抽样。原始库保留在 `data/raw/`，三张 CSV 每次重跑覆盖。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3、Element Plus、ECharts、D3.js |
| 后端 | Flask、Flask RESTful、SQLAlchemy |
| 数据库 | MySQL 8 |
| 文本处理 | HanLP、SikuBERT、jieba、scikit-learn |

## 运行

```bash
# 数据库
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql

# 后端
cd backend
pip install -r requirements.txt
python run.py

# 前端
cd frontend
npm install
npm run dev

# 重新导出人物数据
python scripts/dataPrep/exportCbdb.py
```

后端读取环境变量 `DATABASE_URL`，默认 `mysql+pymysql://root@localhost:3306/historia?charset=utf8mb4`。

## 数据表

`database/schema.sql` 定义十张表：

dynasty、person、person_alias、person_category、person_category_mapping、
document、person_relation、event、event_participant、extraction_record。

## 分工

| 成员 | 方向 |
|---|---|
| A | 前端与可视化 |
| B | 后端与数据库 |
| C | 文本处理与抽取 |

## 文档

`docs/` 按成员分目录，各自维护自己那部分，避免同一文件被多人反复改：

- `docs/zhangcheng/` 系统设计与数据流、接口说明、标注规范、关系分类模型设计
- `docs/huhao/` B 阶段前半段交付记录
- `docs/wangyushan/` personC 语料采集、B 阶段后半段交付记录
- `scripts/README.md` 脚本约定
