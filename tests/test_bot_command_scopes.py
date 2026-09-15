import unittest
from pathlib import Path


class BotCommandScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parents[1]
        cls.bot_init = (root / 'bot' / '__init__.py').read_text(encoding='utf-8')
        cls.scheduler = (root / 'bot' / 'scheduler' / 'bot_commands.py').read_text(encoding='utf-8')

    def test_user_commands_are_split_between_private_and_group_menus(self):
        private = self.bot_init.split('private_user_p = [', 1)[1].split('group_user_p = [', 1)[0]
        group = self.bot_init.split('group_user_p = [', 1)[1].split('admin_only_p = [', 1)[0]

        self.assertIn('BotCommand("start"', private)
        self.assertIn('BotCommand("myinfo"', private)
        self.assertNotIn('BotCommand("red"', private)
        self.assertNotIn('BotCommand("srank"', private)

        self.assertIn('BotCommand("red"', group)
        self.assertIn('BotCommand("srank"', group)
        self.assertNotIn('BotCommand("start"', group)
        self.assertNotIn('BotCommand("myinfo"', group)

    def test_admin_and_owner_commands_remain_in_both_scopes(self):
        self.assertIn('private_admin_p = private_user_p + admin_only_p', self.bot_init)
        self.assertIn('group_admin_p = group_user_p + admin_only_p', self.bot_init)
        self.assertIn('private_owner_p = private_admin_p + owner_only_p', self.bot_init)
        self.assertIn('group_owner_p = group_admin_p + owner_only_p', self.bot_init)

    def test_scheduler_uses_the_matching_command_list_for_each_scope(self):
        self.assertIn(
            'set_bot_commands(private_user_p, scope=BotCommandScopeAllPrivateChats())',
            self.scheduler,
        )
        self.assertIn(
            'set_bot_commands(group_user_p, scope=BotCommandScopeAllGroupChats())',
            self.scheduler,
        )
        self.assertIn(
            'set_bot_commands(private_admin_p, scope=BotCommandScopeChat(chat_id=admin_id))',
            self.scheduler,
        )
        self.assertIn(
            'set_bot_commands(group_admin_p,',
            self.scheduler,
        )
        self.assertIn(
            'set_bot_commands(private_owner_p, scope=BotCommandScopeChat(chat_id=owner))',
            self.scheduler,
        )
        self.assertIn(
            'set_bot_commands(group_owner_p,',
            self.scheduler,
        )


if __name__ == '__main__':
    unittest.main()
