# 接口文档

前缀：`/api/v1`

| 模块 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 人物 | GET | /persons | 人物列表 |
| 人物 | GET | /persons/{id} | 人物详情 |
| 人物 | GET | /persons/{id}/relations | 人物关联关系 |
| 图谱 | GET | /graph?person_id=1&depth=2 | 关系网络 |
| 文本 | POST | /nlp/extract | 执行抽取 |
| 统计 | GET | /statistics/overview | 首页统计 |

## 人物 ID 约定

所有模块共用同一套 `person_id`。文本抽取返回 `person_id`，不返回人名让调用方二次猜测。

## 抽取结果格式

```json
{
  "entities": [{"name": "苏轼", "person_id": 2, "start": 0, "end": 2}],
  "relations": [{"source_id": 2, "target_id": 5, "relation_type": "家族",
                 "confidence": 0.92, "evidence": "苏轼与苏辙同登进士"}],
  "events": []
}
```

`start`、`end` 为 Python 字符串索引，左闭右开。
