# Historia：中国历史人物文本挖掘与知识分析系统

从古籍中识别人物、抽取人物关系，构建跨朝代人物关系图谱。

## 目录

```
historia/
├── frontend/        Vue 3 前端
├── backend/         Flask 后端与文本抽取模块
├── data/            语料、词典、样本
├── database/        建表脚本与种子数据
└── docs/            设计与接口文档
```

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3、Element Plus、ECharts、D3.js |
| 后端 | Flask、Flask RESTful、SQLAlchemy |
| 数据库 | MySQL 8 |
| 文本处理 | HanLP、SikuBERT、jieba、scikit-learn |

## 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
python run.py

# 前端
cd frontend
npm install
npm run dev
```

数据库初始化：

```bash
mysql -u root -p < database/schema.sql
```

## 分工

| 成员 | 方向 |
|---|---|
| A | 前端与可视化 |
| B | 后端与数据库 |
| C | 文本处理与抽取 |

## 文档

- `docs/system_design.md` 系统设计
- `docs/api_documentation.md` 接口文档
