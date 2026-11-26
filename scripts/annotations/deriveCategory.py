"""由官职规则和逐条复核的补充表生成身份表；不连接或修改数据库。"""
import csv
import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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
    people = {r['person_id']: r for r in read_csv(ROOT / 'data/dictionaries/person.csv')}
    rules = read_csv(HERE / 'categoryRules.csv')
    rows = {}
    for office in read_csv(ROOT / 'data/dictionaries/personOffice.csv'):
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
    for row in read_csv(HERE / 'manualCategories.csv'):
        key = (row['person_id'], row['category_name'])
        if key in rows:
            raise ValueError(f'补充表与规则重复：{key}')
        rows[key] = row
    covered = {key[0] for key in rows}
    for pid, person in people.items():
        if pid not in covered:
            rows[(pid, '其他')] = dict(person_id=pid, name=person['name'], category_name='其他',
                source='manual', confidence='1.0',
                evidence='初标占位：现有官职规则和本批文本证据未能确认词表内身份；待复核，不表示此人没有其他身份')
    return sorted(rows.values(), key=lambda r: (int(r['person_id']), r['category_name']))


if __name__ == '__main__':
    result = derive()
    write_preserving_header(ROOT / 'data/annotations/personCategory.csv', result)
    print(f"身份初标：{len(result)}条，覆盖{len({r['person_id'] for r in result})}人；其中其他占位{sum(r['category_name'] == '其他' for r in result)}人")
