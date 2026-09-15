import unittest
from pathlib import Path


class RedMinimumConfirmationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (
            Path(__file__).parents[1]
            / 'bot' / 'modules' / 'extra' / 'red_envelope.py'
        ).read_text(encoding='utf-8')

    def test_less_than_three_members_requires_confirmation_and_normalizes_to_three(self):
        self.assertIn('MIN_RED_MEMBERS = 3', self.source)
        self.assertIn('RED_CONFIRM_TTL_SECONDS = 20', self.source)
        handler = self.source.split('async def send_red_envelop(_, msg):', 1)[1].split(
            '@bot.on_callback_query', 1
        )[0]
        self.assertIn('normalized_members = max(members, MIN_RED_MEMBERS)', handler)
        self.assertIn('if members < MIN_RED_MEMBERS:', handler)
        self.assertIn('return await _request_minimum_members_confirmation(msg, money)', handler)

    def test_confirmation_is_owned_and_sends_only_after_click(self):
        request = self.source.split(
            'async def _request_minimum_members_confirmation', 1
        )[1].split('def _red_confirmation_owner_matches', 1)[0]
        confirm = self.source.split(
            'async def confirm_minimum_red_members', 1
        )[1].split('@bot.on_callback_query', 1)[0]
        self.assertIn("'members': MIN_RED_MEMBERS", request)
        self.assertIn("callback_data=f'red_confirm-{confirm_id}'", request)
        self.assertIn("callback_data=f'red_cancel-{confirm_id}'", request)
        self.assertIn('asyncio.create_task(_expire_red_confirmation(confirm_id))', request)
        self.assertIn('_red_confirmation_owner_matches(call, pending)', confirm)
        self.assertIn("await _send_red_envelope(pending['message'], pending['money'], pending['members'])", confirm)

    def test_confirmation_auto_cancels_and_removes_messages_after_timeout(self):
        expiry = self.source.split('async def _expire_red_confirmation', 1)[1].split(
            'async def _request_minimum_members_confirmation', 1
        )[0]
        self.assertIn('await asyncio.sleep(RED_CONFIRM_TTL_SECONDS)', expiry)
        self.assertIn('pending_red_confirmations.pop(confirm_id, None)', expiry)
        self.assertIn("deleteMessage(pending['message'])", expiry)
        self.assertIn("deleteMessage(pending['prompt'])", expiry)
        self.assertNotIn('_send_red_envelope(', expiry)

    def test_cancel_does_not_send_the_red_envelope(self):
        cancel = self.source.split('async def cancel_minimum_red_members', 1)[1].split(
            '@bot.on_callback_query', 1
        )[0]
        self.assertIn("pending_red_confirmations.pop(confirm_id, None)", cancel)
        self.assertIn("editMessage(call, '❌ 已取消发送红包。')", cancel)
        self.assertNotIn('_send_red_envelope(', cancel)


if __name__ == '__main__':
    unittest.main()
