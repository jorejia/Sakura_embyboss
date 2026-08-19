import unittest
from pathlib import Path


class TgRebindTests(unittest.TestCase):
    def test_expired_archived_account_is_allowed_and_explained(self):
        root = Path(__file__).parents[1]
        panel = (root / 'bot' / 'modules' / 'panel' / 'member_panel.py').read_text(encoding='utf-8')
        buttons = (root / 'bot' / 'func_helper' / 'fix_bottons.py').read_text(encoding='utf-8')

        self.assertIn("and e.lv != 'c'", panel)
        self.assertIn('原TG已注销，或原账号已处于到期封存，均可改绑', panel)
        self.assertIn('账号状态、到期时间、余额、设置和Pro权限等全部保留', panel)
        self.assertIn('TG改绑（注销/到期封存）', buttons)

    def test_rebind_copies_every_account_column_and_deletes_source_atomically(self):
        root = Path(__file__).parents[1]
        sql = (root / 'bot' / 'sql_helper' / 'sql_emby.py').read_text(encoding='utf-8')
        panel = (root / 'bot' / 'modules' / 'panel' / 'member_panel.py').read_text(encoding='utf-8')

        self.assertIn('def sql_rebind_emby(source_tg: int, target_tg: int, require_archived: bool = False):', sql)
        self.assertIn('with_for_update().all()', sql)
        self.assertIn("if require_archived and source.lv != 'c':", sql)
        self.assertIn('for column in Emby.__table__.columns:', sql)
        self.assertIn("if column.name != 'tg':", sql)
        self.assertIn('setattr(target, column.name, getattr(source, column.name))', sql)
        self.assertIn('session.delete(source)', sql)
        self.assertIn('require_archived=original_tg_active', panel)
        self.assertNotIn('embyid=e.embyid, name=e.name, pwd=e.pwd, pwd2=e.pwd2,', panel)


if __name__ == '__main__':
    unittest.main()
