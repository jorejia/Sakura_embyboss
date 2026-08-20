import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

module_path = Path(__file__).parents[1] / 'bot' / 'schemas' / 'schemas.py'
spec = spec_from_file_location('schemas', module_path)
schemas = module_from_spec(spec)
spec.loader.exec_module(schemas)


class LineConfigTests(unittest.TestCase):
    def test_default_line_configuration_marks_third_line_as_pro(self):
        field = schemas.Config.model_fields['line_options']
        options = field.default_factory()
        self.assertEqual([option.id for option in options], [1, 2, 3])
        self.assertEqual([option.pro for option in options], [False, False, True])

    def test_line_id_must_be_positive(self):
        with self.assertRaises(ValueError):
            schemas.LineOption(id=0, name='无效线路')

    def test_config_json_line_options_are_loaded_and_saved(self):
        config = schemas.Config(
            bot_name='test', bot_token='test', owner_api=1, owner_hash='test', owner=1,
            group=[], main_group='test', chanel='test', bot_photo='test', admins=[],
            user_buy={'stat': False, 'text': False, 'button': []},
            open={
                'stat': False, 'timing': 30, 'uplays': True,
                'site': False, 'all_user': 0, 'allow_code': False,
                'checkin': False, 'exchange': False, 'whitelist': False,
                'invite': False, 'leave_ban': False,
            },
            invite='n', money='test', emby_api='test', emby_url='test',
            sidecar_url='test', emby_line='legacy.example', another_line=['legacy'], extra_emby_libs=['legacy'],
            db_host='test', db_user='test', db_pwd='test', db_name='test', ranks={},
            schedall={
                'check_ex': False,
                'dayplayrank': True,
                'weekplayrank': True,
                'low_activity': True,
            },
            default_line_id=1,
            line_options=[
                {'id': 1, 'name': '默认线路', 'pro': False},
                {'id': 3, 'name': 'Pro 三线', 'pro': True},
                {'id': 4, 'name': 'Pro 四线', 'pro': True},
            ],
        )
        self.assertEqual([option.id for option in config.line_options], [1, 3, 4])
        self.assertEqual([option.pro for option in config.line_options], [False, True, True])
        self.assertEqual(config.model_dump()['default_line_id'], 1)
        self.assertEqual([option['id'] for option in config.model_dump()['line_options']], [1, 3, 4])
        dumped = config.model_dump()
        self.assertNotIn('emby_line', dumped)
        self.assertNotIn('another_line', dumped)
        self.assertNotIn('extra_emby_libs', dumped)
        for legacy_field in ('stat', 'timing', 'uplays'):
            self.assertNotIn(legacy_field, dumped['open'])
        for legacy_field in ('check_ex', 'dayplayrank', 'weekplayrank', 'low_activity'):
            self.assertNotIn(legacy_field, dumped['schedall'])
        self.assertTrue(dumped['schedall']['check_ex_paused'])


if __name__ == '__main__':
    unittest.main()
