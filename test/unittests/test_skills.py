import os
import unittest
from os.path import join
from unittest.mock import patch, MagicMock

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestSkillPluginFinders(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.SKILL
    CONFIG_TYPE = PluginConfigTypes.SKILL

    @patch("ovos_plugin_manager.skills.find_plugins")
    def test_find_skill_plugins(self, find_plugins):
        from ovos_plugin_manager.skills import find_skill_plugins
        find_skill_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.skills.find_plugins", return_value={})
    def test_find_skill_plugins_returns_dict(self, _):
        from ovos_plugin_manager.skills import find_skill_plugins
        result = find_skill_plugins()
        self.assertIsInstance(result, dict)


class TestLoadSkillPlugins(unittest.TestCase):

    @patch("ovos_plugin_manager.skills.find_skill_plugins", return_value={})
    def test_load_skill_plugins_no_plugins(self, _):
        from ovos_plugin_manager.skills import load_skill_plugins
        result = load_skill_plugins()
        self.assertEqual(result, [])

    @patch("ovos_plugin_manager.skills.find_skill_plugins")
    def test_load_skill_plugins_success(self, mock_find):
        from ovos_plugin_manager.skills import load_skill_plugins
        skill_instance = MagicMock()
        skill_class = MagicMock(return_value=skill_instance)
        mock_find.return_value = {"my-skill": skill_class}
        result = load_skill_plugins()
        self.assertEqual(result, [skill_instance])
        skill_class.assert_called_once()

    @patch("ovos_plugin_manager.skills.find_skill_plugins")
    def test_load_skill_plugins_handles_exception(self, mock_find):
        from ovos_plugin_manager.skills import load_skill_plugins
        bad_class = MagicMock(side_effect=Exception("boom"))
        good_instance = MagicMock()
        good_class = MagicMock(return_value=good_instance)
        mock_find.return_value = {"bad-skill": bad_class, "good-skill": good_class}
        result = load_skill_plugins()
        self.assertEqual(result, [good_instance])

    @patch("ovos_plugin_manager.skills.find_skill_plugins")
    def test_load_skill_plugins_passes_kwargs(self, mock_find):
        from ovos_plugin_manager.skills import load_skill_plugins
        skill_class = MagicMock(return_value=MagicMock())
        mock_find.return_value = {"my-skill": skill_class}
        fake_bus = MagicMock()
        load_skill_plugins(bus=fake_bus, config={"key": "val"})
        skill_class.assert_called_once_with(bus=fake_bus, config={"key": "val"})


class TestGetSkillDirectories(unittest.TestCase):

    @patch("ovos_plugin_manager.skills.get_xdg_data_dirs", return_value=["/xdg/data"])
    @patch("ovos_plugin_manager.skills.isdir")
    @patch("ovos_plugin_manager.skills.get_default_skills_directory")
    def test_returns_list(self, mock_default, mock_isdir, mock_xdg):
        from ovos_plugin_manager.skills import get_skill_directories
        mock_default.return_value = "/default/skills"
        mock_isdir.return_value = False  # no XDG skill dirs exist
        conf = {"skills": {"directory": "skills"}}
        result = get_skill_directories(conf)
        self.assertIsInstance(result, list)
        self.assertIn("/default/skills", result)

    @patch("ovos_plugin_manager.skills.get_xdg_data_dirs", return_value=["/xdg/data"])
    @patch("ovos_plugin_manager.skills.isdir", return_value=True)
    @patch("ovos_plugin_manager.skills.get_default_skills_directory")
    def test_includes_xdg_dirs_when_they_exist(self, mock_default, mock_isdir, mock_xdg):
        from ovos_plugin_manager.skills import get_skill_directories
        mock_default.return_value = "/default/skills"
        conf = {"skills": {"directory": "skills"}}
        result = get_skill_directories(conf)
        self.assertIn(join("/xdg/data", "skills"), result)

    @patch("ovos_plugin_manager.skills.get_xdg_data_dirs", return_value=[])
    @patch("ovos_plugin_manager.skills.isdir", return_value=True)
    @patch("ovos_plugin_manager.skills.get_default_skills_directory")
    def test_extra_directories_included(self, mock_default, mock_isdir, mock_xdg):
        from ovos_plugin_manager.skills import get_skill_directories
        mock_default.return_value = "/default/skills"
        conf = {"skills": {"directory": "skills",
                            "extra_directories": ["/extra/skills"]}}
        result = get_skill_directories(conf)
        self.assertIn("/extra/skills", result)

    @patch("ovos_plugin_manager.skills.get_xdg_data_dirs", return_value=[])
    @patch("ovos_plugin_manager.skills.isdir", return_value=False)
    @patch("ovos_plugin_manager.skills.get_default_skills_directory")
    def test_extra_dirs_not_added_when_not_isdir(self, mock_default, mock_isdir, mock_xdg):
        from ovos_plugin_manager.skills import get_skill_directories
        mock_default.return_value = "/default/skills"
        conf = {"skills": {"directory": "skills",
                            "extra_directories": ["/nonexistent"]}}
        result = get_skill_directories(conf)
        self.assertNotIn("/nonexistent", result)


class TestGetDefaultSkillsDirectory(unittest.TestCase):

    @patch("ovos_plugin_manager.skills.makedirs")
    @patch("ovos_plugin_manager.skills.get_xdg_data_save_path", return_value="/xdg/save")
    def test_returns_xdg_path_by_default(self, mock_xdg, mock_makedirs):
        from ovos_plugin_manager.skills import get_default_skills_directory
        conf = {"skills": {}}
        result = get_default_skills_directory(conf)
        self.assertIn("/xdg/save", result)
        mock_makedirs.assert_called()

    @patch("ovos_plugin_manager.skills.makedirs")
    @patch("ovos_plugin_manager.skills.get_xdg_data_save_path", return_value="/xdg/save")
    def test_extra_directories_takes_precedence(self, mock_xdg, mock_makedirs):
        from ovos_plugin_manager.skills import get_default_skills_directory
        conf = {"skills": {"extra_directories": ["/my/skills"]}}
        result = get_default_skills_directory(conf)
        self.assertEqual(result, "/my/skills")

    @patch("ovos_plugin_manager.skills.makedirs", side_effect=[PermissionError, None])
    @patch("ovos_plugin_manager.skills.get_xdg_data_save_path", return_value="/xdg/save")
    def test_falls_back_to_xdg_on_permission_error(self, mock_xdg, mock_makedirs):
        from ovos_plugin_manager.skills import get_default_skills_directory
        conf = {"skills": {}}
        result = get_default_skills_directory(conf)
        # Should fall back to xdg save path
        self.assertIn("/xdg/save", result)


class TestGetInstalledSkillIds(unittest.TestCase):

    @patch("ovos_plugin_manager.skills.get_plugin_skills", return_value=([], []))
    @patch("ovos_plugin_manager.skills.get_skill_directories", return_value=[])
    def test_returns_list_with_no_dirs(self, mock_dirs, mock_plugins):
        from ovos_plugin_manager.skills import get_installed_skill_ids
        result = get_installed_skill_ids()
        self.assertIsInstance(result, list)

    @patch("ovos_plugin_manager.skills.get_plugin_skills", return_value=([], ["plugin-skill"]))
    @patch("ovos_plugin_manager.skills.get_skill_directories", return_value=[])
    def test_includes_plugin_skills(self, mock_dirs, mock_plugins):
        from ovos_plugin_manager.skills import get_installed_skill_ids
        result = get_installed_skill_ids()
        self.assertIn("plugin-skill", result)

    @patch("ovos_plugin_manager.skills.get_plugin_skills", return_value=([], []))
    @patch("ovos_plugin_manager.skills.get_skill_directories")
    @patch("ovos_plugin_manager.skills.listdir")
    @patch("ovos_plugin_manager.skills.isdir", return_value=True)
    @patch("ovos_plugin_manager.skills.isfile", return_value=True)
    def test_includes_local_skills(self, mock_isfile, mock_isdir, mock_listdir,
                                   mock_dirs, mock_plugins):
        from ovos_plugin_manager.skills import get_installed_skill_ids
        mock_dirs.return_value = ["/skills"]
        mock_listdir.return_value = ["my-local-skill"]
        result = get_installed_skill_ids()
        self.assertIn("my-local-skill", result)

    @patch("ovos_plugin_manager.skills.get_plugin_skills", return_value=([], ["overlap-skill"]))
    @patch("ovos_plugin_manager.skills.get_skill_directories")
    @patch("ovos_plugin_manager.skills.listdir")
    @patch("ovos_plugin_manager.skills.isdir", return_value=True)
    @patch("ovos_plugin_manager.skills.isfile", return_value=True)
    def test_no_duplicate_when_plugin_and_local_overlap(self, mock_isfile,
                                                         mock_isdir,
                                                         mock_listdir,
                                                         mock_dirs,
                                                         mock_plugins):
        from ovos_plugin_manager.skills import get_installed_skill_ids
        mock_dirs.return_value = ["/skills"]
        mock_listdir.return_value = ["overlap-skill"]
        result = get_installed_skill_ids()
        self.assertEqual(result.count("overlap-skill"), 1)


class TestGetPluginSkills(unittest.TestCase):

    @patch("ovos_plugin_manager.skills.find_skill_plugins", return_value={})
    def test_returns_empty_when_no_plugins(self, _):
        from ovos_plugin_manager.skills import get_plugin_skills
        dirs, ids = get_plugin_skills()
        self.assertEqual(dirs, [])
        self.assertEqual(ids, [])

    @patch("ovos_plugin_manager.skills.importlib.util.find_spec")
    @patch("ovos_plugin_manager.skills.find_skill_plugins")
    def test_returns_dirs_and_ids(self, mock_find, mock_spec):
        import importlib.util
        from ovos_plugin_manager.skills import get_plugin_skills
        skill_cls = MagicMock()
        skill_cls.__module__ = "my_skill"
        mock_find.return_value = {"my-skill-id": skill_cls}
        spec = MagicMock()
        spec.origin = "/path/to/my_skill/__init__.py"
        mock_spec.return_value = spec
        dirs, ids = get_plugin_skills()
        self.assertIn("my-skill-id", ids)
        self.assertIn("/path/to/my_skill", dirs)
