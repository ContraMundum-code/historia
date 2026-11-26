"""身份复核发现的退化风险；Python 标准库 unittest。"""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import deriveCategory as module


class IdentityReviewTests(unittest.TestCase):
    @staticmethod
    def people():
        return [dict(person_id=str(i), name=f'人物{i}', dynasty='唐',
                     birth_year='700', death_year='780') for i in range(1, 189)]

    def test_missing_evidence_fails_instead_of_creating_other(self):
        def read(path):
            return self.people() if path.name == 'person.csv' else []
        with patch.object(module, 'read_csv', side_effect=read):
            with self.assertRaisesRegex(ValueError, '188.*禁止自动填其他'):
                module.derive()

    def test_honorary_offices_and_impossible_dates_are_excluded(self):
        person = dict(birth_year='746', death_year='820')
        base = dict(office_name='同中书门下平章事', first_year='800', last_year='805')
        self.assertTrue(module.valid_office(base, person))
        for change in [dict(office_name='赠同中书门下平章事'),
                       dict(office_name='检校同中书门下平章事'),
                       dict(first_year='728'), dict(last_year='821')]:
            with self.subTest(change=change):
                self.assertFalse(module.valid_office(base | change, person))

    def test_office_cannot_be_borrowed_from_another_person(self):
        tables = {
            'person.csv': self.people(),
            'personOffice.csv': [dict(person_id='187', office_name='知县', first_year='750', last_year='751')],
            'categoryRules.csv': [],
            'reviewedOfficeCategories.csv': [dict(person_id='188', name='人物188', office_name='知县', category_name='政治家', reason='测试错误归属')],
        }
        with patch.object(module, 'read_csv', side_effect=lambda path: tables.get(path.name, [])):
            with self.assertRaisesRegex(ValueError, '缺少有效原始记录：188'):
                module.derive()

    def test_header_bytes_and_quoted_evidence_survive(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sample.csv'
            header = b'\xef\xbb\xbfperson_id,evidence\r\n'
            path.write_bytes(header)
            quote = '原文含逗号,以及换行\n证据第二行'
            module.write_preserving_header(path, [dict(person_id='188', evidence=quote)])
            self.assertEqual(path.read_bytes().splitlines(keepends=True)[0], header)
            with path.open(encoding='utf-8-sig', newline='') as stream:
                self.assertEqual(list(csv.DictReader(stream))[0]['evidence'], quote)


if __name__ == '__main__':
    unittest.main()
