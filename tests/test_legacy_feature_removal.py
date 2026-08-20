import unittest
from pathlib import Path


class LegacyFeatureRemovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).parents[1]

    def test_open_registration_and_activity_retention_are_removed(self):
        schema = (self.root / 'bot' / 'schemas' / 'schemas.py').read_text(encoding='utf-8')
        member_panel = (self.root / 'bot' / 'modules' / 'panel' / 'member_panel.py').read_text(encoding='utf-8')
        sched_panel = (self.root / 'bot' / 'modules' / 'panel' / 'sched_panel.py').read_text(encoding='utf-8')

        for legacy_field in ('stat: bool', 'timing: int', 'low_activity: bool'):
            self.assertNotIn(legacy_field, schema)
        self.assertNotIn('_open.stat', member_panel)
        self.assertNotIn('low_activity', sched_panel)

    def test_watch_time_ranks_and_settlement_are_removed(self):
        schema = (self.root / 'bot' / 'schemas' / 'schemas.py').read_text(encoding='utf-8')
        buttons = (self.root / 'bot' / 'func_helper' / 'fix_bottons.py').read_text(encoding='utf-8')

        self.assertFalse((self.root / 'bot' / 'scheduler' / 'userplays_rank.py').exists())
        for legacy_name in ('dayplayrank', 'weekplayrank', '自动看片结算'):
            self.assertNotIn(legacy_name, schema + buttons)

    def test_extra_libraries_address_setting_and_emby2_are_removed(self):
        python_source = '\n'.join(
            path.read_text(encoding='utf-8')
            for path in (self.root / 'bot').rglob('*.py')
        )
        schema = (self.root / 'bot' / 'schemas' / 'schemas.py').read_text(encoding='utf-8')

        self.assertNotIn('extra_emby_libs', python_source)
        self.assertNotIn('emby_line:', schema)
        self.assertNotIn('sql_emby2', python_source)
        self.assertFalse((self.root / 'bot' / 'sql_helper' / 'sql_emby2.py').exists())


if __name__ == '__main__':
    unittest.main()
