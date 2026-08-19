import unittest
from pathlib import Path


class CodeQueryTests(unittest.TestCase):
    def test_admin_query_accepts_one_code_and_describes_all_code_types(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'modules' / 'panel' / 'admin_panel.py').read_text(encoding='utf-8')

        self.assertIn("filters.regex(r'^ch_link$')", source)
        self.assertIn('record = sql_get_code(code)', source)
        for label in ('普通注册码', '邀请码', '活动码', '直连Pro线路码'):
            self.assertIn(label, source)
        self.assertIn('使用状态', source)
        self.assertIn('使用时间', source)

    def test_delete_is_offered_only_for_unused_code_and_rechecked_in_database(self):
        root = Path(__file__).parents[1]
        panel_source = (root / 'bot' / 'modules' / 'panel' / 'admin_panel.py').read_text(encoding='utf-8')
        sql_source = (root / 'bot' / 'sql_helper' / 'sql_code.py').read_text(encoding='utf-8')

        self.assertIn('can_delete=record.used is None', panel_source)
        self.assertIn('def sql_delete_unused_code(code):', sql_source)
        self.assertIn('with_for_update().first()', sql_source)
        self.assertIn('if record.used is not None:', sql_source)
        self.assertIn('session.delete(record)', sql_source)


if __name__ == '__main__':
    unittest.main()
