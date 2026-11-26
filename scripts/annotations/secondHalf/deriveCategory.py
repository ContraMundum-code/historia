"""由官职规则和逐条复核的补充表生成身份表；不连接或修改数据库。"""
import csv
import io
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FIELDS = ['person_id', 'name', 'category_name', 'source', 'confidence', 'evidence']


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_preserving_header(path, rows):
    """保留现有文件第一行的原始字节（包括 BOM 和换行符）。"""
    header = path.read_bytes().splitlines(keepends=True)[0]
    fields = next(csv.reader([header.decode('utf-8-sig').strip()]))
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator='\n')
    writer.writerows(rows)
    path.write_bytes(header + buffer.getvalue().encode('utf-8'))


def valid_office(row, person):
    # 赠官、检校、散阶与佐职不能直接当作实际任职。
    if re.search('赠|检校|追授|遥领|致仕', row['office_name']):
        return False
    birth, death = int(person['birth_year']), int(person['death_year'])
    for key in ('first_year', 'last_year'):
        value = row[key].strip()
        if value and re.fullmatch(r'-?\d+', value) and not birth <= int(value) <= death:
            return False
    return True


def derive():
    ordered = sorted(read_csv(ROOT / 'data/dictionaries/person.csv'), key=lambda r: int(r['person_id']))
    people = {r['person_id']: r for r in ordered[187:]}
    rules = read_csv(HERE / 'categoryRules.csv')
    rows = {}
    offices = read_csv(ROOT / 'data/dictionaries/personOffice.csv')
    for office in offices:
        if office['person_id'] not in people:
            continue
        person = people[office['person_id']]
        if not valid_office(office, person):
            continue
        for rule in rules:
            if person['dynasty'] not in rule['dynasties'].split('|'):
                continue
            if re.fullmatch(rule['office_pattern'], office['office_name']):
                for category in rule['categories'].split('|'):
                    key = (person['person_id'], category)
                    rows.setdefault(key, dict(person_id=person['person_id'], name=person['name'],
                        category_name=category, source='rule', confidence='0.9',
                        evidence=f"personOffice.csv：{office['office_name']}；规则{rule['rule_id']}"))
    # 对原先漏判的人逐人核对官职，限定到本人和完整官名，不扩大匹配到其他人。
    for decision in read_csv(HERE / 'reviewedOfficeCategories.csv'):
        pid = decision['person_id']
        if pid not in people or decision['name'] != people[pid]['name']:
            raise ValueError(f'复核官职人物超出后半组或姓名不符：{pid}')
        if not any(o['person_id'] == pid and o['office_name'] == decision['office_name']
                   and valid_office(o, people[pid]) for o in offices):
            raise ValueError(f'复核官职缺少有效原始记录：{pid}')
        key = (pid, decision['category_name'])
        if key in rows:
            raise ValueError(f'复核官职与通用规则重复：{key}')
        rows[key] = dict(person_id=pid, name=people[pid]['name'], category_name=key[1],
            source='rule', confidence='0.9',
            evidence=f"personOffice.csv：{decision['office_name']}；逐人复核：{decision['reason']}")
    for row in read_csv(HERE / 'manualCategories.csv'):
        if row['person_id'] not in people or row['name'] != people[row['person_id']]['name']:
            raise ValueError(f'补充表人物超出后半组或姓名不符：{row["person_id"]}')
        key = (row['person_id'], row['category_name'])
        if key in rows:
            raise ValueError(f'补充表与规则重复：{key}')
        rows[key] = row
    covered = {key[0] for key in rows}
    for pid, person in people.items():
        if pid not in covered:
            raise ValueError(f'{pid} {person["name"]} 缺少身份判断：必须逐人填写证据或具体缺项，禁止自动填其他')
    excessive = {pid: count for pid, count in Counter(key[0] for key in rows).items() if count > 4}
    if excessive:
        raise ValueError(f'每人最多4条身份，请保留证据最硬的条目：{excessive}')
    return sorted(rows.values(), key=lambda r: (int(r['person_id']), r['category_name']))


if __name__ == '__main__':
    result = derive()
    path = ROOT / 'data/annotations/personCategory.csv'
    scope = {r['person_id'] for r in result}
    # 合并后运行时保留另一组的行，仅替换自己负责的后半段。
    front = [r for r in read_csv(path) if r['person_id'] not in scope]
    write_preserving_header(path, front + result)
    print(f"身份标注：{len(result)}条，覆盖{len({r['person_id'] for r in result})}人；证据不足保留其他{sum(r['category_name'] == '其他' for r in result)}人")
