import unittest
from pathlib import Path


class AdminStatsTests(unittest.TestCase):
    def test_admin_stats_use_database_and_count_active_line_pro(self):
        root = Path(__file__).parents[1]
        sql_source = (root / 'bot' / 'sql_helper' / 'sql_emby.py').read_text(encoding='utf-8')
        panel_source = (root / 'bot' / 'modules' / 'panel' / 'admin_panel.py').read_text(encoding='utf-8')

        self.assertIn('Emby.line_pro_ex > now', sql_source)
        self.assertIn('tg, emby, white, line_pro = sql_count_emby()', panel_source)
        self.assertIn('有效直连Pro', panel_source)

    def test_server_panel_uses_configured_user_count(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'modules' / 'panel' / 'server_panel.py').read_text(encoding='utf-8')

        self.assertIn('all_user = _open.all_user', source)
        self.assertIn('emby_user = _open.tem', source)
        self.assertNotIn('sql_count_emby', source)

    def test_startup_calibrates_configured_count_from_b_and_c_levels(self):
        root = Path(__file__).parents[1]
        sql_source = (root / 'bot' / 'sql_helper' / 'sql_emby.py').read_text(encoding='utf-8')
        main_source = (root / 'main.py').read_text(encoding='utf-8')

        self.assertIn('Emby.lv.in_(("b", "c"))', sql_source)
        self.assertIn('_calibrate_registered_user_count()', main_source)
        self.assertLess(
            main_source.index('_calibrate_registered_user_count()', main_source.index('async def main()')),
            main_source.index('await bot.start()'),
        )
        self.assertIn("('⭕ 注册上限', 'all_user_limit')", (root / 'bot' / 'func_helper' / 'fix_bottons.py').read_text(encoding='utf-8'))
        self.assertNotIn('open-menu', (root / 'bot' / 'modules' / 'panel' / 'admin_panel.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
