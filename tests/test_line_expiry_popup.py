import unittest
from pathlib import Path


class LineExpiryPopupTests(unittest.TestCase):
    def test_opening_line_menu_clears_expired_pro_and_shows_confirmation_popup(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'modules' / 'panel' / 'member_panel.py').read_text(encoding='utf-8')

        detect = source.index('expired_at = e.line_pro_ex if e.line_pro_ex and e.line_pro_ex <= now else None')
        switch = source.index('await emby.set_use_line(e.embyid, default_line_id)', detect)
        clear = source.index('line_pro_ex=None', switch)
        popup = source.index("callAnswer(call, expiry_notice or '🛣️ 线路选择', expiry_notice is not None)", clear)

        self.assertLess(detect, switch)
        self.assertLess(switch, clear)
        self.assertLess(clear, popup)
        self.assertIn('您的直连Pro权益已于', source)
        self.assertIn('已自动切回普通线路', source)
        self.assertIn('expired_at.strftime("%Y-%m-%d %H:%M:%S")', source)


if __name__ == '__main__':
    unittest.main()
