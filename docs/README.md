# 文档目录

文档按成员分目录，各人维护自己那部分，避免同一个文件被多人反复修改、历史记录交错。

| 目录 | 成员 | 负责内容 |
|---|---|---|
| `zhangcheng/` | 张诚 | 系统设计、接口文档、标注规范、关系分类模型设计 |
| `huhao/` | 胡豪 | B 阶段前半段（person_id 13–16504）交付记录 |
| `wangyushan/` | 王雨杉 | personC 语料采集、B 阶段后半段（17527–189264）交付记录 |

跨成员的共同约定放在各目录之外，目前没有：标注规范的唯一副本在 `zhangcheng/annotationGuidelines.md`，
它约束全部成员，修改前先在群里说一声。

## 各目录文档

`zhangcheng/`

| 文件 | 内容 |
|---|---|
| `system_design.md` | 系统分层、数据流、关系类型 |
| `api_documentation.md` | 接口路由与抽取结果 JSON 格式 |
| `annotationGuidelines.md` | 事件、身份、测试集三类标注的字段与规则 |
| `modelDesign.md` | 关系分类模型的标签体系、结构、训练与推理 |

`huhao/`

| 文件 | 内容 |
|---|---|
| `README.md` | 前半段交付清单 |

`wangyushan/`

| 文件 | 内容 |
|---|---|
| `personC_corpus.md` | personC 段 124 人的语料采集记录 |
| `bSecondHalfBatch01.md` | 后半段身份标注与事件样例的交付说明 |

## 新增文档

放在自己的目录下，文件名用 camelCase，不加 `final`、`v2` 一类后缀。
需要别人引用的，在根 `README.md` 的文档列表里加一行。
