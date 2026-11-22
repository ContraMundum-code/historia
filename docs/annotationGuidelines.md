# 标注规范

适用于事件抽取、人物身份标注、测试集标注三项任务。字段与枚举以 `database/schema.sql`
为准，交付时按本文的 CSV 模板填写，脚本 `scripts/annotations/loadAnnotations.py` 负责校验入库。

## 一、事件抽取

### 1.1 什么算一个事件

史传中记载的、有明确行为主体的、可以给出年份的具体事态。判断标准三条同时成立：

1. 有动作或状态变化，不是身份描述或官职罗列
2. 能落到某一年
3. 能指出参与的具体人物

收录：除授贬谪、战役、出使、上书进谏、弹劾、兴学赈灾、修城池桥梁、著述成书、党争起落、生死葬祭。

不收录：纯履历铺陈（「歷知某州、某府」）、家世交代（「父某，贈某官」）、
无年份的品行评价（「為人峭直耿介」）、他人转述的旁证。

### 1.2 事件表字段

| 字段 | 要求 |
|---|---|
| event_name | 事件名。同一事件在多篇语料出现时用同一名称，便于去重 |
| event_type | 政治、军事、外交、文化、经济、司法、其他，八选一 |
| year | 公元年份整数。原文只有年号纪年时换算后填此列 |
| year_raw | 原文纪年照录，如「元豐五年」「紹興十一年」 |
| location | 发生地，原文无载则留空，不要推测 |
| description | 100–300 字，据原文概述 |
| source_citation | 与 `data/corpus/manifest.csv` 的 `volume` 列一致，如 `宋史/卷338` |
| source_quote | 支撑该事件的原文摘句，照录不改，长度不限 |

描述与摘句的关系：`source_quote` 是证据，`description` 是概述。概述里出现的每个事实
都要能在摘句或同篇语料中找到依据。

### 1.3 去重键

`event_name + year`。同一事件在不同人物的传里都出现时，只建一条，参与者累加。

例：《宋史》苏轼传与苏辙传都记乌台诗案，只建一条，参与者写两条。

### 1.4 参与者表字段

| 字段 | 要求 |
|---|---|
| event_id | 事件编号，入库时由脚本回填，CSV 阶段用事件名占位 |
| person_id | 必须是 `data/dictionaries/person.csv` 里的 person_id |
| role | 主角、主谋、参与者、支持者、反对者、受害者、见证者、其他，八选一 |

`主角` 每事件限一人，是事件叙述的中心人物。多方并立的事（如战役双方主将）都写 `主角`
以外的角色，或按「主角」分别建两个事件。

### 1.5 CSV 模板

`data/annotations/event.csv`：

```csv
event_name,event_type,year,year_raw,location,description,source_citation,source_quote
烏臺詩案,司法,1079,元豐二年,御史臺獄,蘇軾因詩文被劾謗訕朝政，下御史臺獄，後貶黃州。,宋史/卷338,……
```

`data/annotations/eventParticipant.csv`：

```csv
event_name,year,person_id,role
烏臺詩案,1079,3767,主角
烏臺詩案,1079,1493,支持者
```

## 二、人物身份标注

### 2.1 词表

现有人物身份九个，固定不新增，标不出就写「其他」：

政治家、军事家、文学家、诗人、思想家、史学家、书法家、宰相、将领、其他

「政治家」与「宰相」不互斥。拜相者两个都标：宰相是具体职任，政治家是活动领域。

### 2.2 一律不得为空

374 人每人至少一条 `person_category_mapping`。判不出来就标「其他」，
不得留空，不得省略整行。

一人可有多条身份，如欧阳修标文学家、史学家、政治家三条。

### 2.3 三条来源

| source | 含义 | confidence |
|---|---|---|
| cbdb | 直接取 CBDB 的 `POSTED_TO_OFFICE_DATA` 官职名 | 1.0 |
| rule | 由官职名按规则映射，如 `同中書門下平章事`→宰相 | 0.9 |
| manual | 人工判断，CBDB 无官职记录或官职推不出身份时 | 1.0 |

规则映射写在 `scripts/annotations/deriveCategory.py` 里，规则表单独成 CSV，便于复核。

### 2.4 CSV 模板

`data/annotations/personCategory.csv`：

```csv
person_id,name,category_name,source,confidence,evidence
3767,蘇軾,文学家,rule,0.9,禮部尚書/翰林學士
3767,蘇軾,政治家,manual,1.0,
```

`evidence` 填支撑该身份的官职名或判断理由，manual 行可留空。

## 三、测试集标注

### 3.1 选句标准

三条件同时成立：句中出现两个及以上已收录人物；人物之间存在可判定的关系；关系能在
句内找到语言证据（称谓、动作、官职、亲属词）。

不选：指代不明无法消解代词的句子、只有一人出现的句子、关系需靠上下文数段才能判定的句子、
语料本身残缺的句子。

### 3.2 一句多关系

一句话里存在多对关系时，每对写一行，共用同一 `sentence_id`。

### 3.3 与弱标注隔离

测试集句子不得出现在弱标注结果里。切分按文献和人物分，不按句子随机分。

### 3.4 CSV 模板

`data/annotations/testSet.csv`：

```csv
sentence_id,sentence,person_a,person_b,relation_type,evidence,document_volume
T0001,軾與轍兄弟友愛，……,蘇軾,蘇轍,家族,兄弟,宋史/卷338
```

关系类型取 `data/dictionaries/relations.csv` 的六类：师生、家族、朋友、合作、对立、君臣。

## 四、交付前自检

跑 `python scripts/annotations/checkAnnotations.py`，四项不通过不得提交：

1. 事件表 `event_name+year` 无重复
2. 参与者表 person_id 全部存在于 `person.csv`
3. 身份表覆盖 374 人，无空缺
4. 测试集句子与弱标注结果无交集
