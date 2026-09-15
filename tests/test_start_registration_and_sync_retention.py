import unittest
from pathlib import Path


class StartRegistrationAndSyncRetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parents[1]
        cls.start = (root / 'bot' / 'modules' / 'commands' / 'start.py').read_text(encoding='utf-8')
        cls.syncs = (root / 'bot' / 'modules' / 'commands' / 'syncs.py').read_text(encoding='utf-8')

    def test_private_start_creates_placeholder_before_group_check(self):
        handler = self.start.split('async def p_start(_, msg):', 1)[1].split(
            '# 返回面板', 1
        )[0]
        create_record = handler.index('sql_add_emby(msg.from_user.id)')
        group_check = handler.index('if not await user_in_group_filter(_, msg):')
        self.assertLess(create_record, group_check)
        self.assertEqual(handler.count('sql_add_emby(msg.from_user.id)'), 1)
        self.assertIn('加入群组后', handler)
        self.assertNotIn('回来点 /start', handler)

    def test_syncgroupm_keeps_the_local_user_row(self):
        handler = self.syncs.split('async def sync_emby_group(_, msg):', 1)[1].split(
            '@bot.on_message', 1
        )[0]
        self.assertIn('await emby.emby_del(i.embyid)', handler)
        self.assertNotIn('sql_delete_emby(', handler)
        self.assertIn('账号删除，用户记录保留', handler)


if __name__ == '__main__':
    unittest.main()
