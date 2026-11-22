import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


def read(*parts):
    return (ROOT.joinpath(*parts)).read_text(encoding='utf-8')


class AdminMenuReorgTests(unittest.TestCase):
    def test_removed_and_moved_commands_are_gone(self):
        sources = ''.join(read(*p) for p in [
            ('bot', '__init__.py'), ('bot', 'modules', 'commands', 'syncs.py'),
            ('bot', 'modules', 'panel', 'sched_panel.py'), ('bot', 'modules', 'panel', 'config_panel.py'),
        ])
        for cmd in ('deleted', 'embyadmin', 'bindall_id', 'syncgroupm', 'syncunbound', 'check_ex',
                    'days_ranks', 'week_ranks', 'backup_db', 'restart', 'config'):
            self.assertNotRegex(sources, rf"filters\.command\('{cmd}'", cmd)
            self.assertNotIn(f'BotCommand("{cmd}"', sources, cmd)

    def test_maintenance_menu_exposes_moved_tasks(self):
        panel = read('bot', 'modules', 'panel', 'maintain_panel.py')
        for data in ('mtask_exp', 'mtask_day', 'mtask_week', 'mtask_grp', 'mtask_unb', 'mtask_bak', 'mtask_rst'):
            self.assertIn(f"'{data}'", panel)
        buttons = read('bot', 'func_helper', 'fix_bottons.py')
        for data in ("'lnadm'", "'xacct'", "'mtask'"):
            self.assertIn(data, buttons)

    def test_new_callbacks_do_not_collide_with_unanchored_patterns(self):
        sources = ''.join(p.read_text(encoding='utf-8') for p in (ROOT / 'bot').rglob('*.py'))
        unanchored = {m for m in re.findall(r"filters\.regex\('([^'^]+)'\)", sources)}
        panel = read('bot', 'modules', 'panel', 'maintain_panel.py')
        datas = set(re.findall(r"'((?:lnadm|xacct|mtask)[a-z_]*)", panel))
        for data in datas:
            for pattern in unanchored:
                if pattern in ('manage',) and data == 'manage':
                    continue
                self.assertIsNone(re.search(pattern, data), f'{data} would also trigger {pattern}')

    def test_lines_come_from_sidecar(self):
        for parts in [('bot', 'func_helper', 'fix_bottons.py'), ('bot', 'modules', 'panel', 'member_panel.py'),
                      ('bot', 'modules', 'panel', 'kk.py'), ('bot', 'scheduler', 'check_ex.py'),
                      ('bot', 'modules', 'commands', 'exchange.py'), ('bot', 'modules', 'panel', 'admin_panel.py')]:
            source = read(*parts)
            self.assertNotRegex(source, r'(?<![\w.(])line_options(?![\w(])', parts)
            self.assertNotRegex(source, r'(?<![\w.])default_line_id(?!\w)', parts)
        self.assertIn('"/admin/lines"', read('bot', 'func_helper', 'emby.py'))

    def test_unbound_cleanup_previews_before_deleting(self):
        panel = read('bot', 'modules', 'panel', 'maintain_panel.py')
        preview = panel.index('async def maintain_unbound(')
        confirm = panel.index('async def maintain_unbound_ok(')
        self.assertNotIn('delete_unbound_accounts(', panel[preview:confirm])
        self.assertIn('delete_unbound_accounts(', panel[confirm:])


if __name__ == '__main__':
    unittest.main()
