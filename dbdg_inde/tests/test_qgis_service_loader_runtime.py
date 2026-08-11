import os
import unittest


try:
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtWidgets import QApplication, QListWidgetItem
    from qgis.core import QgsApplication

    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


@unittest.skipUnless(QGIS_AVAILABLE, "Requer o runtime Python do QGIS")
class ServiceLoaderQgisRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.qgis_app = QgsApplication.instance() or QgsApplication([], False)
        cls.qgis_app.initQgis()

        from ..service_loader_dialog import ServiceLoaderDialog

        cls.dialog_class = ServiceLoaderDialog

    @classmethod
    def tearDownClass(cls):
        if cls.qgis_app:
            cls.qgis_app.exitQgis()

    def setUp(self):
        original_load_catalog = self.dialog_class.load_catalog
        self.dialog_class.load_catalog = lambda _self: None
        try:
            self.dialog = self.dialog_class()
        finally:
            self.dialog_class.load_catalog = original_load_catalog

    def tearDown(self):
        self.dialog.close()
        QApplication.processEvents()

    def _select_service(self, service_type):
        class FakeHandler:
            @staticmethod
            def list_layers(_entry):
                return [("camada_teste", "Camada teste", None)]

        self.dialog.handlers[service_type] = FakeHandler()
        service_list = self.dialog.service_widgets[service_type]
        service_list.blockSignals(True)
        item = QListWidgetItem("Instituição teste")
        item.setData(Qt.UserRole, {"url": "https://example.invalid/ows"})
        service_list.addItem(item)
        service_list.setCurrentItem(item)
        service_list.blockSignals(False)
        self.dialog.show_layers(service_type)

    def test_lists_layers_for_all_service_types(self):
        for service_type in ("wms", "wfs", "wcs"):
            with self.subTest(service_type=service_type):
                self._select_service(service_type)
                self.assertEqual(self.dialog.layer_list.count(), 1)
                self.assertEqual(self.dialog.layer_list.item(0).text(), "Camada teste")

    def test_spatial_buttons_require_selected_wfs_layer(self):
        self._select_service("wfs")
        self.assertFalse(self.dialog.wfs_bbox_map_button.isEnabled())
        self.assertFalse(self.dialog.wfs_advanced_filter_button.isEnabled())

        self.dialog.layer_list.setCurrentRow(0)
        QApplication.processEvents()
        self.assertTrue(self.dialog.wfs_bbox_map_button.isEnabled())
        self.assertTrue(self.dialog.wfs_advanced_filter_button.isEnabled())

    def test_generates_filter_encoding_from_polygon_wkt(self):
        from ..wfs_filter_dialogs import SpatialFilterDialog

        dialog = SpatialFilterDialog(geometry_property="the_geom")
        dialog.wkt_input.setPlainText(
            "POLYGON((-43.80 -23.10,-43.10 -23.10,-43.10 -22.70,"
            "-43.80 -22.70,-43.80 -23.10))"
        )
        dialog._generate()
        generated_filter = dialog.filter_text()
        dialog.close()

        self.assertIn("<fes:Intersects>", generated_filter)
        self.assertIn("<fes:ValueReference>the_geom</fes:ValueReference>", generated_filter)
        self.assertIn("<gml:Polygon", generated_filter)
        self.assertIn('srsName="EPSG:4326"', generated_filter)
        self.assertIn("-43.8 -23.1", generated_filter)

    def test_switching_tabs_clears_layers_from_previous_service(self):
        self._select_service("wms")
        self.assertEqual(self.dialog.layer_list.count(), 1)

        self.dialog.tabs.setCurrentIndex(1)
        QApplication.processEvents()

        self.assertEqual(self.dialog.current_service_type, "wfs")
        self.assertEqual(self.dialog.current_layers, [])
        self.assertEqual(self.dialog.layer_list.count(), 0)
        self.assertFalse(self.dialog.load_button.isEnabled())
        self.assertFalse(self.dialog.metadata_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
