import unittest
from datetime import datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

module_path = Path(__file__).parents[1] / 'bot' / 'func_helper' / 'line_access.py'
spec = spec_from_file_location('line_access', module_path)
line_access = module_from_spec(spec)
spec.loader.exec_module(line_access)

configured_line = line_access.configured_line
line_pro_active = line_access.line_pro_active
line_pro_status_text = line_access.line_pro_status_text
line_pro_trial_expiry = line_access.line_pro_trial_expiry
line_pro_trial_available = line_access.line_pro_trial_available
line_requires_pro = line_access.line_requires_pro
visible_lines = line_access.visible_lines
revoke_line_pro_access = line_access.revoke_line_pro_access


class LineAccessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 30, 12, 0, 0)
        self.lines = [
            SimpleNamespace(id=1, name='直连一线', pro=False),
            SimpleNamespace(id=2, name='直连二线', pro=False),
            SimpleNamespace(id=3, name='直连三线', pro=True),
            SimpleNamespace(id=4, name='直连四线', pro=True),
        ]

    def test_pro_status_uses_expiry(self):
        future = self.now + timedelta(days=30)
        self.assertTrue(line_pro_active(future, now=self.now))
        self.assertEqual(line_pro_status_text(future, now=self.now), '2026-08-29 12:00:00')
        self.assertFalse(line_pro_active(self.now, now=self.now))
        self.assertEqual(line_pro_status_text(self.now, now=self.now), '未激活')
        self.assertEqual(line_pro_status_text(None, now=self.now), '未激活')

    def test_trial_starts_now_without_active_pro(self):
        self.assertEqual(line_pro_trial_expiry(None, now=self.now), self.now + timedelta(days=1))
        self.assertEqual(line_pro_trial_expiry(self.now, now=self.now), self.now + timedelta(days=1))

    def test_trial_extends_existing_active_pro(self):
        current_expiry = self.now + timedelta(days=30)
        self.assertEqual(line_pro_trial_expiry(current_expiry, now=self.now),
                         current_expiry + timedelta(days=1))

    def test_trial_button_requires_unused_chance_and_no_active_pro(self):
        self.assertTrue(line_pro_trial_available(0, None, now=self.now))
        self.assertFalse(line_pro_trial_available(1, None, now=self.now))
        self.assertFalse(line_pro_trial_available(
            0, self.now + timedelta(days=1), now=self.now))

    def test_paid_lines_are_hidden_without_pro(self):
        self.assertEqual([line.id for line in visible_lines(self.lines, False)], [1, 2])
        self.assertEqual([line.id for line in visible_lines(self.lines, True)], [1, 2, 3, 4])

    def test_configured_line_and_permission(self):
        self.assertEqual(configured_line(self.lines, 3).name, '直连三线')
        self.assertTrue(line_requires_pro(self.lines, 3))
        self.assertTrue(line_requires_pro(self.lines, 4))
        self.assertFalse(line_requires_pro(self.lines, 2))
        self.assertIsNone(configured_line(self.lines, 99))


class RevokeLineProTests(unittest.IsolatedAsyncioTestCase):
    async def test_switches_line_before_clearing_permission(self):
        events = []

        async def set_use_line(emby_id, line_id):
            events.append(('line', emby_id, line_id))
            return True, line_id

        def clear_permission():
            events.append(('database',))
            return True

        result = await revoke_line_pro_access('emby-user', 1, set_use_line, clear_permission)
        self.assertEqual(result, (True, None, None))
        self.assertEqual(events, [('line', 'emby-user', 1), ('database',)])

    async def test_does_not_clear_permission_when_line_switch_fails(self):
        cleared = False

        async def set_use_line(_emby_id, _line_id):
            return False, 'sidecar unavailable'

        def clear_permission():
            nonlocal cleared
            cleared = True
            return True

        result = await revoke_line_pro_access('emby-user', 1, set_use_line, clear_permission)
        self.assertEqual(result, (False, 'line', 'sidecar unavailable'))
        self.assertFalse(cleared)


if __name__ == '__main__':
    unittest.main()
