import unittest
from unittest.mock import patch

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes
from ovos_plugin_manager.skills import get_skill_directories, get_default_skills_directory


class TestSkills(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.SKILL
    CONFIG_TYPE = PluginConfigTypes.SKILL
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.skills import find_skill_plugins
        find_skill_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    
    def test_get_skill_directories(self):
        # Default directory
        mock_config = {'skills': {}}
        default_directories = get_skill_directories(mock_config)
        for directory in default_directories:
            self.assertEqual(basename(directory), 'skills')
        # Configured directory
        mock_config['skills']['directory'] = 'test'
        test_directories = get_skill_directories(mock_config)
        for directory in test_directories:
            self.assertEqual(basename(directory), 'test')
        self.assertEqual(len(default_directories), len(test_directories))

    def test_get_default_skills_directory(self):
        # Default directory
        mock_config = {'skills': {}}
        default_dir = get_default_skills_directory(mock_config)
        self.assertTrue(isdir(default_dir))
        self.assertEqual(basename(default_dir), 'skills')
        self.assertEqual(dirname(dirname(default_dir)), self.test_data_path)
        # Override directory
        mock_config['skills']['directory'] = 'test'
        test_dir = get_default_skills_directory(mock_config)
        self.assertTrue(isdir(test_dir))
        self.assertEqual(basename(test_dir), 'test')
        self.assertEqual(dirname(dirname(test_dir)), self.test_data_path)
        
    def test_load_skill_plugins(self):
        from ovos_plugin_manager.skills import load_skill_plugins
        # TODO
