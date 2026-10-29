import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


class PluginPackageTest(unittest.TestCase):
    def test_zip_has_runtime_modules_and_no_repository_or_cache(self):
        script = Path(__file__).resolve().parents[1] / 'tools' / 'package_plugin.py'
        spec = importlib.util.spec_from_file_location('package_plugin', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            output = module.build_package(Path(directory) / 'plugin.zip')
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                self.assertIsNone(archive.testzip())
                for name in ('metadata.txt', '__init__.py', 'dbdg_inde_plugin.py',
                             'service_loader_dialog.py', 'wfs_filter_dialogs.py',
                             'wfs_attribute_filter.py', 'service_handlers/wfs_handler.py',
                             'defusedxml/ElementTree.py'):
                    self.assertIn('dbdg_inde/' + name, names)
                for name in names:
                    self.assertTrue(name.startswith('dbdg_inde/'))
                    self.assertNotIn('.git', name.split('/'))
                    self.assertNotIn('__pycache__', name.split('/'))
                    self.assertNotIn('tests', name.split('/'))
                    self.assertFalse(name.endswith(('.pyc', '.pyo')))
                    self.assertLess(len(name), 150)
