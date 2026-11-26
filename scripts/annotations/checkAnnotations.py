"""只读校验 B 标注；不执行数据库操作，不宣称已检查尚未制作的 C 测试集。"""
import csv
import re
from collections import Counter
from pathlib import Path
from deriveCategory import derive, read_csv

ROOT = Path(__file__).resolve().parents[2]
ANN = ROOT / 'data/annotations'
HEADERS = {
    'event.csv': 'event_name,event_type,year,year_raw,location,description,source_citation,source_quote',
    'eventParticipant.csv': 'event_name,year,person_id,role',
    'personCategory.csv': 'person_id,name,category_name,source,confidence,evidence',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check():
    for filename, header in HEADERS.items():
        with (ANN / filename).open(encoding='utf-8-sig', newline='') as stream:
            require(stream.readline().rstrip('\r\n') == header, f'{filename}表头变化')
            for row in csv.reader(stream):
                require(len(row) == len(header.split(',')), f'{filename}列数异常')
    people = {r['person_id']: r for r in read_csv(ROOT / 'data/dictionaries/person.csv')}
    manifest = read_csv(ROOT / 'data/corpus/manifest.csv')
    texts = {}
    volumes = {}
    for row in manifest:
        path = ROOT / 'data/corpus' / f"{row['person_id']}_{row['name']}.txt"
        if path.exists():
            text = path.read_text(encoding='utf-8-sig')
            texts[row['person_id']] = text
            volumes.setdefault(row['volume'], []).append(text)
    events = read_csv(ANN / 'event.csv')
    participants = read_csv(ANN / 'eventParticipant.csv')
    categories = read_csv(ANN / 'personCategory.csv')
    keys = {(r['event_name'], r['year']) for r in events}
    require(len(keys) == len(events), '事件重复')
    for row in events:
        require(row['event_type'] in '政治 军事 外交 文化 经济 司法 其他'.split(), '事件类型无效')
        require(re.fullmatch(r'-?\d+', row['year']), '年份须为整数')
        require(100 <= len(row['description']) <= 300, f"描述长度异常：{row['event_name']}")
        require(row['year_raw'] and row['year_raw'] in row['source_quote'], '纪年未在摘句中出现')
        require(any(row['source_quote'] in text for text in volumes.get(row['source_citation'], [])),
                f"原文不能逐字追溯：{row['event_name']}")
    principal = Counter()
    participant_keys = set()
    for row in participants:
        key = (row['event_name'], row['year'])
        require(key in keys and row['person_id'] in people, '参与者引用无效')
        require(row['role'] in '主角 主谋 参与者 支持者 反对者 受害者 见证者 其他'.split(), '角色无效')
        participant_key = (*key, row['person_id'])
        require(participant_key not in participant_keys, '参与者重复')
        participant_keys.add(participant_key)
        p = people[row['person_id']]
        require(int(p['birth_year']) <= int(row['year']) <= int(p['death_year']), '参与者生卒与事件年份冲突')
        if row['role'] == '主角':
            principal[key] += 1
    require(all(principal[key] == 1 for key in keys), '本批每个事件须且仅有一位主角')
    category_keys = set()
    for row in categories:
        pid = row['person_id']
        require(pid in people and row['name'] == people[pid]['name'], '身份人物引用无效')
        require(row['category_name'] in '政治家 军事家 文学家 诗人 思想家 史学家 书法家 宰相 将领 其他'.split(), '身份类别无效')
        require((row['source'], row['confidence']) in [('manual', '1.0'), ('rule', '0.9'), ('cbdb', '1.0')], '来源或置信度无效')
        require(row['evidence'], '身份初标必须留证据或待核原因')
        key = (pid, row['category_name'])
        require(key not in category_keys, '身份重复')
        category_keys.add(key)
        if row['source'] == 'manual' and row['category_name'] != '其他':
            quote = row['evidence'].split('：「', 1)[1][:-1]
            require(re.sub(r'\s+', '', quote) in re.sub(r'\s+', '', texts.get(pid, '')),
                    f'身份引文不在本传中：{pid}')
    require({r['person_id'] for r in categories} == set(people), '身份未覆盖全部人物')
    require(categories == derive(), '身份输出与规则、补充表不一致')
    others = {r['person_id'] for r in categories if r['category_name'] == '其他'}
    reviewed = {r['person_id'] for r in read_csv(ANN / 'bReview.csv') if r['item'] == '身份初标'}
    require(others == reviewed, '其他占位必须逐人进入待复核清单')
    print(f'B校验通过：{len(events)}事件、{len(participants)}参与记录、{len(categories)}身份记录；覆盖{len(people)}人，其他待复核{len(others)}人。')
    print('本检查验证格式、引用及证据存在性；历史判断和初标身份仍需审核。C测试集和弱标注隔离检查不在本批范围。')


if __name__ == '__main__':
    check()
