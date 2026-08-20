import unittest
from pathlib import Path


class ProActivationAutoLineTests(unittest.TestCase):
    def test_line_code_switches_only_for_new_activation(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'modules' / 'commands' / 'exchange.py').read_text(encoding='utf-8')

        self.assertIn('was_pro_active = line_pro_active(user.line_pro_ex, now=now)', source)
        self.assertIn('activation_line = pro_activation_line(line_options, user.line_pro_ex, now=now)', source)
        self.assertIn('if activation_line is not None:', source)
        self.assertIn('await emby.set_use_line(emby_id, activation_line.id)', source)
        self.assertIn('"续期" if was_pro_active else "激活"', source)

    def test_line_code_requires_an_active_emby_account_before_consumption(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'modules' / 'commands' / 'exchange.py').read_text(encoding='utf-8')

        self.assertIn('当前无账号请先使用注册码注册账号', source)
        self.assertIn('您的账号已到期，请先使用续费码续费账号', source)
        helper = source.index('def _line_code_account_error(user):')
        no_account = source.index('if user is None or not user.embyid:', helper)
        expired = source.index("if user.lv == 'c':", helper)
        locked_user = source.index('with_for_update().first()', source.index('async def _redeem_line_code'))
        locked_check = source.index('account_error = _line_code_account_error(user)', locked_user)
        consume_code = source.index('updated = session.query(Code)', locked_check)
        line_branch = source.index("if code_type == 'l':", source.index('async def rgs_code'))
        missing_bot_user = source.index('if not data:', line_branch)
        self.assertLess(no_account, expired)
        self.assertLess(locked_check, consume_code)
        self.assertLess(line_branch, missing_bot_user)

    def test_trial_switches_to_first_pro_line_after_permission_is_granted(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'modules' / 'panel' / 'member_panel.py').read_text(encoding='utf-8')

        claim = source.index('expires_at = sql_claim_line_pro_trial(call.from_user.id)')
        switch = source.index('await emby.set_use_line(e.embyid, activation_line.id)', claim)
        self.assertLess(claim, switch)
        self.assertIn('activation_line = pro_activation_line(line_options, e.line_pro_ex, now=now)', source)


if __name__ == '__main__':
    unittest.main()
