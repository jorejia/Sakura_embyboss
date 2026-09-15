import unittest
from pathlib import Path


class PrivateUnauthorizedGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (
            Path(__file__).parents[1]
            / 'bot' / 'modules' / 'commands' / 'start.py'
        ).read_text(encoding='utf-8')

    def test_guard_runs_before_regular_private_handlers_and_excludes_start(self):
        self.assertIn(
            "@bot.on_message(filters.private & ~filters.command('start', prefixes), group=-1)",
            self.source,
        )

    def test_guard_only_blocks_unauthorized_users_in_non_hidden_mode(self):
        guard = self.source.split('async def reject_unauthorized_private', 1)[1].split(
            '# 反命令提示', 1
        )[0]
        self.assertIn('if not _open.site or await user_in_group_filter(_, msg):', guard)
        self.assertIn(
            '当前未加入MICU社区群，无法使用机器人功能',
            guard,
        )
        self.assertIn('/start', guard)
        self.assertIn('msg.stop_propagation()', guard)


if __name__ == '__main__':
    unittest.main()
