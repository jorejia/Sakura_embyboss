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

    def test_trial_switches_to_first_pro_line_after_permission_is_granted(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'modules' / 'panel' / 'member_panel.py').read_text(encoding='utf-8')

        claim = source.index('expires_at = sql_claim_line_pro_trial(call.from_user.id)')
        switch = source.index('await emby.set_use_line(e.embyid, activation_line.id)', claim)
        self.assertLess(claim, switch)
        self.assertIn('activation_line = pro_activation_line(line_options, e.line_pro_ex, now=now)', source)


if __name__ == '__main__':
    unittest.main()
