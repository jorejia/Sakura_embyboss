import unittest
from pathlib import Path


class ActivityCodeUsageTests(unittest.TestCase):
    def test_generated_activity_codes_have_refreshable_usage_button(self):
        root = Path(__file__).parents[1]
        panel = (root / 'bot' / 'modules' / 'panel' / 'admin_panel.py').read_text(encoding='utf-8')
        buttons = (root / 'bot' / 'func_helper' / 'fix_bottons.py').read_text(encoding='utf-8')

        self.assertIn("('🔍 查询使用', 'activity_usage')", buttons)
        self.assertIn('buttons=activity_usage_ikb', panel)
        self.assertIn("filters.regex(r'^activity_usage$')", panel)
        self.assertIn("status = '✅ 已使用'", panel)
        self.assertIn("status = '⭕ 未使用'", panel)
        self.assertIn("line.split('  —  ', 1)", panel)

    def test_usage_query_is_limited_to_activity_codes(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'sql_helper' / 'sql_code.py').read_text(encoding='utf-8')

        self.assertIn('def sql_get_activity_code_usage(codes):', source)
        self.assertIn('Code.code.in_(codes)', source)
        self.assertIn("Code.invite == 'a'", source)


if __name__ == '__main__':
    unittest.main()
