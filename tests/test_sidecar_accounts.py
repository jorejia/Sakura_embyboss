import unittest
from pathlib import Path


class SidecarAccountTests(unittest.TestCase):
    """账号已迁到 emby-sidecar：账号相关操作不能再写 Emby 原后端。"""

    def setUp(self):
        root = Path(__file__).parents[1]
        self.source = (root / 'bot' / 'func_helper' / 'emby.py').read_text(encoding='utf-8')

    def test_account_operations_do_not_call_emby_user_endpoints(self):
        for legacy in ('/emby/Users/New', '/Policy\'', '/Password\'', '/emby/Users/AuthenticateByName',
                       "f'{self.url}/emby/Users/{id}'", '/FavoriteItems/'):
            self.assertNotIn(legacy, self.source, legacy)

    def test_account_operations_use_sidecar_admin_api(self):
        for path in ('"/admin/users"', '/admin/users/{id}/password', '/admin/users/{id}/policy',
                     '"/admin/users/authenticate"', '/admin/users/{user_id}/favorites/{item_id}'):
            self.assertIn(path, self.source, path)

    def test_only_images_still_use_emby_backend(self):
        import re
        for line in self.source.splitlines():
            code = line.split('#', 1)[0]
            if re.search(r'self\.url\}|emby_url\}', code):
                self.assertIn('/Images/', code, line)
        for gone in ('user_usage_stats', 'Items/Counts?api_key', 'get_emby_report', 'get_emby_userip'):
            self.assertNotIn(gone, self.source, gone)
        for path in ('/admin/items/counts', '"/admin/items/search"', '/admin/items/{item_id}'):
            self.assertIn(path, self.source, path)

    def test_internal_calls_send_admin_token_header(self):
        self.assertNotIn('self._internal_parental_rating_url(),\n                headers=self.headers', self.source)
        self.assertIn('X-Admin-Token', self.source)


if __name__ == '__main__':
    unittest.main()
