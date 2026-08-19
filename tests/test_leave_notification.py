import unittest
from pathlib import Path


class LeaveNotificationTests(unittest.TestCase):
    def test_active_leave_success_sends_private_notice_only_in_active_leave_branch(self):
        source = (
            Path(__file__).parents[1]
            / 'bot' / 'modules' / 'callback' / 'leave_delemby.py'
        ).read_text(encoding='utf-8')

        active_branch, banned_branch = source.split(
            'elif event.old_chat_member and event.new_chat_member:', 1
        )
        self.assertIn('您因退出MICU社区群失去社区福利包括账号', source)
        self.assertIn('await _notify_active_leave_user(user_id)', active_branch)
        self.assertNotIn('await _notify_active_leave_user(user_id)', banned_branch)
        self.assertIn('except Exception as error:', source)


if __name__ == '__main__':
    unittest.main()
