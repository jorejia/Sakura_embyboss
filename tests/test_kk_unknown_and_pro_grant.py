import unittest
from pathlib import Path


class KkUnknownAndProGrantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parents[1]
        cls.kk = (root / 'bot' / 'modules' / 'panel' / 'kk.py').read_text(encoding='utf-8')
        cls.buttons = (root / 'bot' / 'func_helper' / 'fix_bottons.py').read_text(encoding='utf-8')
        cls.sql = (root / 'bot' / 'sql_helper' / 'sql_emby.py').read_text(encoding='utf-8')

    def test_unknown_telegram_user_uses_database_and_keeps_management_panel(self):
        self.assertIn("return False, '未识别'", self.kk)
        self.assertIn('if not recognized and sql_get_emby(tg=uid) is None:', self.kk)
        self.assertIn('text, keyboard = await cr_kk_ikb(uid, first_name)', self.kk)
        self.assertIn('async def _refresh_kk_panel(call, tgid):', self.kk)

    def test_pro_button_changes_between_one_day_grant_and_revoke(self):
        self.assertIn("if line_pro == '未激活':", self.buttons)
        self.assertIn("['🎁 赋予直连Pro 1天', f'line_pro_grant-{uid}']", self.buttons)
        self.assertIn("['🧹 解除直连Pro', f'line_pro_revoke-{uid}']", self.buttons)

    def test_one_day_grant_is_atomic_and_auto_switches_to_first_pro_line(self):
        self.assertIn('def sql_grant_line_pro(tg: int, days: int = 1, now=None):', self.sql)
        self.assertIn('with_for_update().first()', self.sql)
        self.assertIn('if line_pro_active(user.line_pro_ex, now=now):', self.sql)
        self.assertIn('user.line_pro_ex = now + timedelta(days=days)', self.sql)
        self.assertIn("filters.regex(r'^line_pro_grant-\\d+$')", self.kk)
        self.assertIn('target_line = first_pro_line(line_options)', self.kk)
        self.assertIn('await emby.set_use_line(emby_id, target_line.id)', self.kk)


if __name__ == '__main__':
    unittest.main()
