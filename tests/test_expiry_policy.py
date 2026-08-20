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

    def test_weighted_conversion_runs_after_pro_and_coin_renewal(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'scheduler' / 'check_ex.py').read_text(encoding='utf-8')
        sql_source = (root / 'bot' / 'sql_helper' / 'sql_emby.py').read_text(encoding='utf-8')

        pro_check = source.index('await check_line_pro_expired()')
        account_query = source.index("Emby.ex < datetime.now(), Emby.lv == 'b'")
        coin_renewal = source.index('_open.exchange and r.iv >= _open.exchange_cost * 30')
        weighted_conversion = source.index('sql_convert_expiry_by_weight(')
        self.assertLess(pro_check, account_query)
        self.assertLess(coin_renewal, weighted_conversion)
        self.assertIn("if convert_status == 'success':", source)
        self.assertIn('await bot.send_message(r.tg, text)', source[weighted_conversion:])

        helper = sql_source[sql_source.index('def sql_convert_expiry_by_weight('):]
        self.assertIn("if not line_pro_active(user.line_pro_ex, now=now):", helper)
        self.assertIn('if expires_at <= now + timedelta(days=1):', helper)
        self.assertIn('user.ex = expires_at', helper)
        self.assertIn('user.line_pro_ex = expires_at', helper)
        self.assertIn('with_for_update()', helper)


if __name__ == '__main__':
    unittest.main()
