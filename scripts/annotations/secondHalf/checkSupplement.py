"""只读检查王雨杉第二批 B 标注；不连接数据库、不修改数据。

运行：python scripts/annotations/secondHalf/checkSupplement.py --base-ref origin/main
历史纪年、主体消歧及外部引文仍需沿来源人工审核，检查通过不表示历史终审通过。
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone, timedelta
import io
import logging
from pathlib import Path
import re
import subprocess

from deriveCategory import derive, read_csv

ROOT = Path(__file__).resolve().parents[3]
ANN = ROOT / 'data/annotations'
HEADERS = {
    'event.csv': 'event_name,event_type,year,year_raw,location,description,source_citation,source_quote',
    'eventParticipant.csv': 'event_name,year,person_id,role',
    'personCategory.csv': 'person_id,name,category_name,source,confidence,evidence',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def key(row):
    return row['event_name'], str(row['year'])


def normalize(text):
    return re.sub(r'\s+', '', text)


def check(base_ref=None):
    people = {r['person_id']: r for r in read_csv(ROOT / 'data/dictionaries/person.csv')}
    scope = {p['person_id'] for p in sorted(people.values(), key=lambda p: int(p['person_id']))[187:]}
    manifests = {r['person_id']: r for r in read_csv(ROOT / 'data/corpus/manifest.csv')}
    texts = {}
    for pid, person in people.items():
        path = ROOT / 'data/corpus' / f"{pid}_{person['name']}.txt"
        if path.exists():
            texts[pid] = path.read_text(encoding='utf-8-sig')
    for filename, header in HEADERS.items():
        path = ANN / filename
        require(path.read_text(encoding='utf-8-sig').splitlines()[0] == header, f'表头变化：{filename}')
        with path.open(encoding='utf-8-sig', newline='') as stream:
            require(all(len(row) == len(header.split(',')) for row in csv.reader(stream)), f'列数错误：{filename}')
    events = read_csv(ANN / 'event.csv')
    parts = read_csv(ANN / 'eventParticipant.csv')
    cats = read_csv(ANN / 'personCategory.csv')
    event_map = {key(r): r for r in events}
    require(len(event_map) == len(events), '事件名和年份重复')
    require(len({(*key(r), r['person_id']) for r in parts}) == len(parts), '同事件同人物参与记录重复')
    require(all(key(r) in event_map and r['person_id'] in people for r in parts), '参与者引用无效')
    batch = read_csv(ANN / 'bBatch02Events.csv')
    batch_keys = {key(r) for r in batch}
    require(len(batch_keys) == len(batch) and batch_keys <= event_map.keys(), '第二批事件缺失或重复')
    metadata = {key(r): r for r in read_csv(ANN / 'bEventEvidence.csv')}
    for row in batch:
        pid = row['person_id']; event = event_map[key(row)]
        require(pid in scope, '新增事件主角超出后187人')
        require(key(row) in metadata and metadata[key(row)]['year_basis'] == row['year_basis'], '纪年依据索引不一致')
        require(row['year_basis'] and row['location_basis'], '缺纪年或地点依据')
        require(event['event_type'] in '政治 军事 外交 文化 经济 司法 其他'.split(), '事件类型错误')
        require(100 <= len(event['description']) <= 300, f'描述长度：{key(row)}')
        require(event['year'].isdigit(), '年份不是整数')
        require(event['year_raw'] in event['source_quote'], f'原纪年不在摘句：{key(row)}')
        require(event['source_citation'] == manifests[pid]['volume'], '出处不是来源人物manifest卷次')
        require(event['source_quote'].replace('\r\n', '\n') in texts.get(pid, ''), f'原文不能逐字追溯：{key(row)}')
        principals = [p for p in parts if key(p) == key(row) and p['role'] == '主角']
        require(len(principals) == 1 and principals[0]['person_id'] == pid, '实际主角与来源索引不符')
    actor_notes = read_csv(ANN / 'bBatch02Participants.csv')
    require({(*key(p), p['person_id'], p['role']) for p in actor_notes} ==
            {(*key(p), p['person_id'], p['role']) for p in parts if key(p) in batch_keys}, '参与者判断清单与主表不一致')
    for actor in actor_notes:
        person = people[actor['person_id']]
        require(actor['name'] == person['name'] and actor['reason'], '参与者姓名或依据缺失')
        require(actor['role'] in '主角 主谋 参与者 支持者 反对者 受害者 见证者 其他'.split(), '参与角色错误')
        require(int(person['birth_year']) <= int(actor['year']) <= int(person['death_year']), '参与者生卒与事件年份冲突')
    for pending in read_csv(ANN / 'bPendingParticipants.csv'):
        require(key(pending) in batch_keys and pending['actor_name'] and pending['reason'], '待补人物缺事件或说明')
    require(len({(r['person_id'], r['category_name']) for r in cats}) == len(cats), '身份重复')
    require({r['person_id'] for r in cats} == set(people), '身份未覆盖374人')
    require(all(n <= 4 for n in Counter(r['person_id'] for r in cats).values()), '身份超过4条')
    own = [r for r in cats if r['person_id'] in scope]
    require(own == derive(), '身份表与规则、补充表生成结果不一致')
    require(all('初标占位' not in r['evidence'] and r['evidence'] for r in own), '存在泛化占位或无证据身份')
    for row in own:
        require(row['name'] == people[row['person_id']]['name'], '身份姓名不符')
        require(row['category_name'] in '政治家 军事家 文学家 诗人 思想家 史学家 书法家 宰相 将领 其他'.split(), '身份类别非法')
        require((row['source'],row['confidence']) in [('manual','1.0'),('rule','0.9'),('cbdb','1.0')], '身份来源或置信度非法')
    references = read_csv(Path(__file__).resolve().parent / 'manualSourceReferences.csv')
    refmap = {(r['person_id'],r['category_name']): r for r in references}
    require(len(refmap) == len(references), '身份来源索引重复')
    for row in own:
        if row['source'] != 'manual' or row['category_name'] == '其他':
            continue
        reference = refmap.get((row['person_id'],row['category_name']))
        if reference:
            require(row['evidence'] == reference['source_citation']+'：「'+reference['source_quote']+'」', '身份引文与索引不符')
            require(reference['reason'], '身份判断理由缺失')
            if reference['source_url']:
                require(reference['source_url'].startswith('https://') and not reference['source_person_id'], '外部来源格式错误')
                continue  # 不用离线脚本伪称验证了外部网页的历史事实。
            origin = reference['source_person_id']; quote = reference['source_quote']
            require(reference['source_citation'] == manifests[origin]['volume'], '身份引文卷次不符')
        else:
            origin = row['person_id'];quote = row['evidence'].split('：「',1)[1][:-1]
        require(normalize(quote) in normalize(texts.get(origin,'')), '本地身份引文不能追溯')
    changes = read_csv(ANN / 'bBatch02Categories.csv')
    require(all((r['person_id'],r['category_name']) in {(c['person_id'],c['category_name']) for c in own} for r in changes), '身份补充索引引用不存在的标签')
    others = {r['person_id'] for r in own if r['category_name'] == '其他'}
    pending_ids = {r['person_id'] for r in read_csv(ANN / 'bReview.csv') if r['item'] == '身份初标'}
    require(others == pending_ids, '其他与逐人缺项清单不一致')
    inventory = read_csv(ANN/'bSecondHalfInventory.csv')
    require(len(inventory) == len(scope) and {r['person_id'] for r in inventory} == scope, '后187人交付对账不完整或重复')
    for item in inventory:
        labels = {r['category_name'] for r in own if r['person_id'] == item['person_id']}
        require(set(item['categories'].split('|')) == labels and int(item['category_count']) == len(labels), '逐人身份对账不符')
        require(int(item['event_count_as_main']) == sum(r['person_id'] == item['person_id'] for r in metadata.values()), '逐人事件对账不符')
    if base_ref:
        def baseline(path):
            return subprocess.check_output(['git','show',f'{base_ref}:{path}'], cwd=ROOT)
        for filename in HEADERS:
            path = f'data/annotations/{filename}'
            raw = baseline(path)
            require((ROOT/path).read_bytes().splitlines()[0] == raw.splitlines()[0], '表头字节/BOM与基线不符')
            old = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
            current = read_csv(ROOT/path)
            if filename == 'personCategory.csv':
                require([r for r in current if r['person_id'] not in scope] == [r for r in old if r['person_id'] not in scope], '前半组身份被改动')
            else:
                require(current[:len(old)] == old, '原有事件或参与者被覆盖')
        changed = subprocess.check_output(['git','diff',base_ref,'--name-only','--','database','data/dictionaries','data/corpus'],cwd=ROOT)
        require(not changed, '数据库、词典或原始语料存在改动')
    logging.info('第二批：%s事件、%s参与记录、%s身份补充；后187人%s条身份，其他%s人。',len(batch),len(actor_notes),len(changes),len(own),len(others))
    logging.info('通过格式、来源索引、引文存在性、去重、覆盖、上限和保留原数据检查；纪年/主体解释及外部引文仍需人工审核。')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-ref')
    args = parser.parse_args()
    (ROOT/'logs').mkdir(exist_ok=True)
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d_%H%M%S')
    logging.basicConfig(level=logging.INFO,format='%(message)s',handlers=[logging.StreamHandler(),logging.FileHandler(ROOT/'logs'/f'checkBSecondHalfSupplement_{stamp}.log',encoding='utf-8')])
    check(args.base_ref)
