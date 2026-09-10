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

    def test_ban_is_offered_for_used_code_and_deletes_code_after_penalty(self):
        root = Path(__file__).parents[1]
        panel_source = (root / 'bot' / 'modules' / 'panel' / 'admin_panel.py').read_text(encoding='utf-8')
        sql_source = (root / 'bot' / 'sql_helper' / 'sql_code.py').read_text(encoding='utf-8')
        button_source = (root / 'bot' / 'func_helper' / 'fix_bottons.py').read_text(encoding='utf-8')

        self.assertIn("('🚫 封禁注册码', f'rcode_ban:{code}')", button_source)
        self.assertIn("filters.regex(r'^rcode_ban:')", panel_source)
        self.assertIn('can_ban=record.used is not None', panel_source)
        self.assertIn('def sql_ban_used_code(code, now=None):', sql_source)
        self.assertIn('with_for_update().first()', sql_source)
        self.assertIn('expires_at - timedelta(days=days)', sql_source)
        self.assertIn('session.delete(record)', sql_source)
        self.assertNotIn('bannedtime', sql_source)
        self.assertIn("if expiry_kind == 'line_pro':", sql_source)
        self.assertIn("'status': 'revoke_line_required'", sql_source)
        self.assertIn('def sql_revoke_line_pro_code(code, expected_tg):', sql_source)
        self.assertIn('user.line_pro_ex = None', sql_source)
        self.assertIn('await revoke_line_pro_access(', panel_source)
        self.assertIn('Emby 账号 | **保留，不受影响**', panel_source)
        self.assertIn('await emby.emby_del(result[\'embyid\'])', panel_source)
        self.assertLess(
            sql_source.index("'status': 'revoke_line_required'"),
            sql_source.index("'status': 'delete_required'"),
        )
        self.assertLess(
            panel_source.index("if status == 'revoke_line_required':"),
            panel_source.index("if status == 'delete_required':"),
        )
        self.assertIn('sql_delete_used_code(code, tg)', panel_source)
        self.assertIn('您因使用非法注册码，现已扣除 {days} 天时长。', panel_source)
        self.assertIn('您因使用非法注册码，现已被删除账号。', panel_source)


if __name__ == '__main__':
    unittest.main()
