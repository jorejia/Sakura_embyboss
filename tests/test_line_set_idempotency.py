import unittest
from pathlib import Path


class LineSetIdempotencyTests(unittest.TestCase):
    def test_same_line_is_success_without_sending_set_request(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'func_helper' / 'emby.py').read_text(encoding='utf-8')
        method = source[source.index('    async def set_use_line'):source.index(
            '    # async def get_remote_image_by_id', source.index('    async def set_use_line'))]

        precheck = method.index('current_ok, current_value = await self.get_use_line(user_id)')
        same_line = method.index('if current_ok and current_value == requested_value:', precheck)
        request = method.index('resp = r.get(', same_line)
        self.assertLess(precheck, same_line)
        self.assertLess(same_line, request)
        self.assertIn('return True, current_value', method[same_line:request])

    def test_failed_or_timed_out_set_is_verified_against_backend_state(self):
        root = Path(__file__).parents[1]
        source = (root / 'bot' / 'func_helper' / 'emby.py').read_text(encoding='utf-8')
        method = source[source.index('    async def set_use_line'):source.index(
            '    # async def get_remote_image_by_id', source.index('    async def set_use_line'))]

        request = method.index('resp = r.get(')
        verification = method.index('verified, actual_value = await self.get_use_line(user_id)', request)
        recovered = method.index('if verified and actual_value == requested_value:', verification)
        self.assertLess(request, verification)
        self.assertLess(verification, recovered)
        self.assertIn('return True, actual_value', method[recovered:])


if __name__ == '__main__':
    unittest.main()
