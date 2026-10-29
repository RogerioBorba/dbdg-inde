import os
import unittest
from unittest.mock import patch


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
        item.setData(
            Qt.ItemDataRole.UserRole, {"url": "https://example.invalid/ows"}
        )
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

    def test_attribute_dialog_and_layer_scoping(self):
        from ..wfs_filter_dialogs import AttributeFilterDialog
        dialog = AttributeFilterDialog([('nome', 'text'), ('pop', 'integer')])
        dialog.operator_combo.setCurrentIndex(dialog.operator_combo.findData('contains'))
        dialog.value_input.setText('Brasília')
        self.assertIn('PropertyIsLike', dialog.filter_text())
        dialog.operator_combo.setCurrentIndex(dialog.operator_combo.findData('in'))
        dialog.value_input.setText("'RJ', 'ES', 'MG'")
        self.assertIn('Or', dialog.filter_text())
        self.assertIn("'RJ'", dialog.value_input.placeholderText())
        dialog.field_combo.setCurrentIndex(1)
        self.assertEqual(dialog.operator_combo.findData('contains'), -1)
        self.assertEqual(dialog.operator_combo.findData('in'), -1)
        dialog.value_input.setText('100000')
        dialog.operator_combo.setCurrentIndex(dialog.operator_combo.findData('gt'))
        self.assertIn('PropertyIsGreaterThan', dialog.filter_text())
        dialog.close()
        self._select_service('wfs')
        self.dialog.layer_list.setCurrentRow(0)
        key = self.dialog._attribute_key()
        self.dialog.wfs_attribute_filters[key] = (('pop', 'gt', '100000'), dialog.filter_text())
        self.dialog._update_wfs_filter_buttons()
        self.assertTrue(self.dialog.wfs_attribute_clear_button.isEnabled())
        self.dialog.clear_attribute_filter()
        self.assertFalse(self.dialog.wfs_attribute_clear_button.isEnabled())

    def test_attribute_bbox_count_and_download_share_filter(self):
        from ..wfs_attribute_filter import attribute_filter
        from .. import service_loader_dialog
        from xml.etree import ElementTree as ET
        self._select_service('wfs')
        self.dialog.layer_list.setCurrentRow(0)
        key = self.dialog._attribute_key()
        self.dialog.wfs_attribute_filters[key] = (
            ('pop', 'gt', '100000'), attribute_filter('pop', 'integer', 'gt', '100000'))
        self.dialog.wfs_bbox_input.setText('-48,-16,-46,-14,EPSG:4326')
        self.dialog.wfs_count_input.setText('10')
        received = {}
        class Handler:
            def get_geometry_property(self, *args):
                return 'geom'
            def get_feature_count(self, **kwargs):
                received['count'] = kwargs
                return 1
            def create_layer(self, **kwargs):
                received['download'] = kwargs['options']
                return None
        self.dialog.handlers['wfs'] = Handler()
        with patch.object(service_loader_dialog.QMessageBox, 'warning'):
            self.dialog.add_layer()
        self.assertEqual(received['count']['filter_encoding'], received['download']['filter_encoding'])
        self.assertIsNone(received['download']['bbox'])
        self.assertEqual(received['download']['count'], 10)
        root = ET.fromstring(received['download']['filter_encoding'])
        self.assertTrue(root[0].tag.endswith('And'))

    def test_reopening_attribute_form_starts_blank_and_cancel_preserves_filter(self):
        from .. import service_loader_dialog
        from ..wfs_filter_dialogs import AttributeFilterDialog
        from unittest.mock import Mock
        self._select_service('wfs')
        self.dialog.layer_list.setCurrentRow(0)
        key = self.dialog._attribute_key()
        saved = (('nome', 'in', "'RJ', 'MG'"), '<saved/>')
        self.dialog.wfs_attribute_filters[key] = saved
        self.dialog.handlers['wfs'].get_attribute_fields = Mock(return_value=[('nome', 'text')])
        opened = []
        class InspectDialog(AttributeFilterDialog):
            def exec(self):
                opened.append((self.operator_combo.currentData(), self.value_input.text()))
                return self.DialogCode.Rejected
        with patch.object(service_loader_dialog, 'AttributeFilterDialog', InspectDialog):
            self.dialog.open_attribute_filter()
        self.assertEqual(opened, [('eq', '')])
        self.assertEqual(self.dialog.wfs_attribute_filters[key], saved)

    def test_zero_matches_skips_download_and_layer_addition(self):
        from .. import service_loader_dialog
        from qgis.core import QgsProject
        from unittest.mock import Mock
        self._select_service('wfs')
        self.dialog.layer_list.setCurrentRow(0)
        handler = Mock()
        handler.get_feature_count.return_value = 0
        self.dialog.handlers['wfs'] = handler
        before = set(QgsProject.instance().mapLayers())
        with patch.object(service_loader_dialog.QMessageBox, 'information') as notice, \
                patch.object(service_loader_dialog.QMessageBox, 'critical'):
            self.dialog.add_layer()
        handler.create_layer.assert_not_called()
        self.assertEqual(set(QgsProject.instance().mapLayers()), before)
        self.assertIn('Nenhuma', notice.call_args.args[2])

    def test_downloaded_empty_layer_is_not_added_even_with_explicit_limit(self):
        from .. import service_loader_dialog
        from qgis.core import QgsProject, QgsVectorLayer
        from unittest.mock import Mock
        self._select_service('wfs')
        self.dialog.layer_list.setCurrentRow(0)
        self.dialog.wfs_startindex_input.setText('0')
        self.dialog.wfs_count_input.setText('10')
        empty = QgsVectorLayer('Point?crs=EPSG:4326', 'vazia', 'memory')
        self.assertTrue(empty.isValid())
        handler = Mock()
        handler.create_layer.return_value = empty
        self.dialog.handlers['wfs'] = handler
        before = set(QgsProject.instance().mapLayers())
        with patch.object(service_loader_dialog.QMessageBox, 'information') as notice, \
                patch.object(service_loader_dialog.QMessageBox, 'critical'):
            self.dialog.add_layer()
        try:
            self.assertEqual(set(QgsProject.instance().mapLayers()), before)
            self.assertIn('Nenhuma', notice.call_args.args[2])
        finally:
            QgsProject.instance().removeMapLayer(empty.id())



if __name__ == "__main__":
    unittest.main()
