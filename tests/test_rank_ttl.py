import unittest
from pathlib import Path


class RankTtlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (
            Path(__file__).parents[1]
            / 'bot' / 'modules' / 'extra' / 'red_envelope.py'
        ).read_text(encoding='utf-8')

    def test_rank_cache_and_message_share_three_minute_ttl(self):
        self.assertIn('RANK_TTL_SECONDS = 180', self.source)
        self.assertIn('@cache.memoize(ttl=RANK_TTL_SECONDS)', self.source)
        self.assertIn('timer=RANK_TTL_SECONDS', self.source)


if __name__ == '__main__':
    unittest.main()
