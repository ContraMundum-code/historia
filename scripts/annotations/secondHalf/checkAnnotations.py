"""只读校验 B 标注；不执行数据库操作，不宣称已检查尚未制作的 C 测试集。"""
import csv
import re
from collections import Counter
from pathlib import Path
from deriveCategory import derive, read_csv

ROOT = Path(__file__).resolve().parents[3]
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
    scope = {r['person_id'] for r in sorted(people.values(), key=lambda r: int(r['person_id']))[187:]}
    manifest = read_csv(ROOT / 'data/corpus/manifest.csv')
    texts = {}
    volumes = {}
    for row in manifest:
        path = ROOT / 'data/corpus' / f"{row['person_id']}_{row['name']}.txt"
        if path.exists():
            text = path.read_text(encoding='utf-8-sig')
            texts[row['person_id']] = text
            volumes.setdefault(row['volume'], []).append(text)
    # 只检查本批事件及身份；允许前半组的记录在合并后共存。
    batch_keys = {(r['event_name'], r['year']) for r in read_csv(ANN / 'bEventEvidence.csv')}
    events = [r for r in read_csv(ANN / 'event.csv') if (r['event_name'], r['year']) in batch_keys]
    require({(r['event_name'], r['year']) for r in events} == batch_keys, '本批事件缺失')
    participants = [r for r in read_csv(ANN / 'eventParticipant.csv') if (r['event_name'], r['year']) in batch_keys]
    categories = [r for r in read_csv(ANN / 'personCategory.csv') if r['person_id'] in scope]
    keys = {(r['event_name'], r['year']) for r in events}
    require(len(keys) == len(events), '事件重复')
    for row in events:
        require(row['event_type'] in '政治 军事 外交 文化 经济 司法 其他'.split(), '事件类型无效')
        require(re.fullmatch(r'-?\d+', row['year']), '年份须为整数')
        require(100 <= len(row['description']) <= 300, f"描述长度异常：{row['event_name']}")
        require(row['year_raw'] and row['year_raw'] in row['source_quote'], '纪年未在摘句中出现')
        # Windows Git 检出可能把 CSV 引文内的换行改为 CRLF。
        quote = row['source_quote'].replace('\r\n', '\n')
        require(any(quote in text for text in volumes.get(row['source_citation'], [])),
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
    references = read_csv(Path(__file__).resolve().parent / 'manualSourceReferences.csv')
    reference_map = {(r['person_id'], r['category_name']): r for r in references}
    require(len(reference_map) == len(references), '身份引文索引重复')
    for row in categories:
        pid = row['person_id']
        require(pid in people and row['name'] == people[pid]['name'], '身份人物引用无效')
        require(row['category_name'] in '政治家 军事家 文学家 诗人 思想家 史学家 书法家 宰相 将领 其他'.split(), '身份类别无效')
        require((row['source'], row['confidence']) in [('manual', '1.0'), ('rule', '0.9'), ('cbdb', '1.0')], '来源或置信度无效')
        require(row['evidence'], '身份初标必须留证据或待核原因')
        require('初标占位' not in row['evidence'], '禁止使用统一初标占位说明')
        key = (pid, row['category_name'])
        require(key not in category_keys, '身份重复')
        category_keys.add(key)
        if row['source'] == 'manual' and row['category_name'] != '其他':
            quote = row['evidence'].split('：「', 1)[1][:-1]
            reference = reference_map.get(key)
            if reference:
                require(row['evidence'] == reference['source_citation'] + '：「' + reference['source_quote'] + '」', '引文与索引不一致')
                require(reference['reason'], '补充身份缺判断理由')
                if reference['source_url']:
                    require(reference['source_url'].startswith('https://') and not reference['source_person_id'], '外部引文来源格式无效')
                else:
                    require(reference['source_person_id'] in texts, '跨传证据文件缺失')
                    require(re.sub(r'\s+', '', quote) in re.sub(r'\s+', '', texts[reference['source_person_id']]), '本地补充引文不在指定传记中')
            else:
                require(re.sub(r'\s+', '', quote) in re.sub(r'\s+', '', texts.get(pid, '')),
                        f'身份引文不在本传中：{pid}')
    require(set(reference_map) <= category_keys, '引文索引引用了不存在的身份')
    require({r['person_id'] for r in categories} == scope, '身份未覆盖后187人')
    require(all(count <= 4 for count in Counter(r['person_id'] for r in categories).values()), '每人身份不能超过4条')
    require(categories == derive(), '身份输出与规则、补充表不一致')
    others = {r['person_id'] for r in categories if r['category_name'] == '其他'}
    reviewed = {r['person_id'] for r in read_csv(ANN / 'bReview.csv') if r['item'] == '身份初标'}
    require(others == reviewed, '其他占位必须逐人进入待复核清单')
    audit = read_csv(ANN / 'bIdentityReview.csv')
    require(len(audit) == len({r['person_id'] for r in audit}) == 73, '原73人复核记录不完整或重复')
    for item in audit:
        actual = {r['category_name'] for r in categories if r['person_id'] == item['person_id']}
        require(actual == set(item['new_categories'].split('|')), '逐人复核结果与主表不一致')
        if item['person_id'] in others:
            require(item['remaining_issue'] and item['remaining_issue'] in item['evidence'], '其他缺少本人具体缺项')
    print(f'B后半段校验通过：{len(events)}事件、{len(participants)}参与记录、{len(categories)}身份记录；覆盖{len(scope)}人，其他待复核{len(others)}人。')
    print('本地引文验证存在性；外部引文只验证来源索引，需沿链接审核。历史判断仍需审核；不检查C测试集与弱标注隔离。')


if __name__ == '__main__':
    check()
