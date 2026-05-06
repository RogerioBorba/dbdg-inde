import sys
import types
import unittest
import importlib.util
from pathlib import Path


def _install_qgis_stubs():
    if "qgis" in sys.modules:
        return

    qgis_module = types.ModuleType("qgis")
    pyqt_module = types.ModuleType("qgis.PyQt")
    qtwidgets_module = types.ModuleType("qgis.PyQt.QtWidgets")
    core_module = types.ModuleType("qgis.core")

    class _DummyApplication:
        @staticmethod
        def processEvents():
            return None

    class _DummyMessageBox:
        Yes = 1
        No = 2

        @staticmethod
        def question(*args, **kwargs):
            return _DummyMessageBox.No

    class _Dummy:
        def __init__(self, *args, **kwargs):
            pass

    qtwidgets_module.QApplication = _DummyApplication
    qtwidgets_module.QMessageBox = _DummyMessageBox
    core_module.QgsCoordinateReferenceSystem = _Dummy
    core_module.QgsFeature = _Dummy
    core_module.QgsGeometry = _Dummy
    core_module.QgsVectorLayer = _Dummy
    core_module.QgsWkbTypes = _Dummy

    sys.modules["qgis"] = qgis_module
    sys.modules["qgis.PyQt"] = pyqt_module
    sys.modules["qgis.PyQt.QtWidgets"] = qtwidgets_module
    sys.modules["qgis.core"] = core_module


_install_qgis_stubs()


def _load_wfs_handler_class():
    root_dir = Path(__file__).resolve().parents[1]
    package_name = "dbdg_inde_testpkg"

    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(root_dir)]
    sys.modules[package_name] = package_module

    service_handlers_module = types.ModuleType(f"{package_name}.service_handlers")
    service_handlers_module.__path__ = [str(root_dir / "service_handlers")]
    sys.modules[f"{package_name}.service_handlers"] = service_handlers_module

    module_path = root_dir / "service_handlers" / "wfs_handler.py"
    spec = importlib.util.spec_from_file_location(
        f"{package_name}.service_handlers.wfs_handler",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.WfsServiceHandler


WfsServiceHandler = _load_wfs_handler_class()


class WfsHandlerSrsSelectionTest(unittest.TestCase):
    def test_shape_zip_omits_srs_name(self):
        self.assertIsNone(WfsServiceHandler._preferred_srs_name("shape-zip"))
        self.assertEqual(
            WfsServiceHandler._effective_output_format("shape-zip"),
            "application/json",
        )

    def test_other_formats_keep_epsg4326(self):
        self.assertEqual(
            WfsServiceHandler._preferred_srs_name("application/gml+xml"),
            "EPSG:4326",
        )
        self.assertEqual(
            WfsServiceHandler._preferred_srs_name("application/json"),
            "EPSG:4326",
        )
        self.assertEqual(
            WfsServiceHandler._effective_output_format("application/gml+xml"),
            "application/gml+xml",
        )

if __name__ == "__main__":
    unittest.main()
