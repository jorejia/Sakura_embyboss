import unittest
from pathlib import Path


class StartJoinPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parents[1]
        cls.buttons = (root / 'bot' / 'func_helper' / 'fix_bottons.py').read_text(encoding='utf-8')
        cls.start = (root / 'bot' / 'modules' / 'commands' / 'start.py').read_text(encoding='utf-8')

    def test_join_panel_only_contains_the_group(self):
        panel = self.buttons.split('# un in group', 1)[1].split('"""members', 1)[0]
        self.assertIn("f't.me/{main_group}'", panel)
        self.assertNotIn('chanel', panel)
        self.assertNotIn('上新通知频道', panel)

    def test_join_prompts_no_longer_mention_the_channel(self):
        self.assertNotIn('群组和频道', self.start)


if __name__ == '__main__':
    unittest.main()
