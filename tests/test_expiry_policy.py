import unittest
from pathlib import Path


class ExpiryPolicyTests(unittest.TestCase):
    def test_only_active_user_balance_auto_renewal_remains(self):
        source = (Path(__file__).parents[1] / 'bot' / 'scheduler' / 'check_ex.py').read_text(encoding='utf-8')

        self.assertIn('_open.exchange and r.iv >= _open.exchange_cost * 30', source)
        self.assertNotIn('r.us >= 30', source)
        self.assertNotIn('c.us >= 30', source)
        self.assertNotIn('c.iv >= _open.exchange_cost * 30', source)
        self.assertNotIn('解封账户', source)

    def test_expiry_task_has_persistent_pause_guard_and_catches_past_dates(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'scheduler' / 'check_ex.py').read_text(encoding='utf-8')
        panel_source = (root / 'bot' / 'modules' / 'panel' / 'sched_panel.py').read_text(encoding='utf-8')
        buttons_source = (root / 'bot' / 'func_helper' / 'fix_bottons.py').read_text(encoding='utf-8')

        self.assertIn('if schedall.check_ex_paused:', source)
        self.assertIn("return 'paused'", source)
        self.assertIn('Emby.ex < datetime.now()', source)
        self.assertNotIn('Emby2', source)
        self.assertNotIn('sql_emby2', source)
        self.assertIn("scheduler.add_job(check_expired, 'cron'", panel_source)
        self.assertNotIn('sched-check_ex', buttons_source)


if __name__ == '__main__':
    unittest.main()
