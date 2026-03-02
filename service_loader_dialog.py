# -*- coding: utf-8 -*-
"""
Dialog for browsing INDE catalog and loading WMS/WFS/WCS layers.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)
from qgis.core import QgsProject
import unicodedata

from .catalog_client import fetch_catalog
from .metadata_viewer import MetadataSummaryDialog, fetch_metadata_summary
from .service_handlers import build_service_handlers


class ServiceLoaderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("INDE OGC service loader")
        self.resize(800, 500)

        self.handlers = build_service_handlers()
        self.service_widgets = {}
        self.current_service_type = None
        self.catalog = []
        self.current_layers = []

        self.tabs = QTabWidget()
        self.filter_input = QLineEdit()
        self.layer_filter_input = QLineEdit()
        self.layer_list = QListWidget()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["GML (default)", "Shapefile (zip)", "JSON"])
        self.load_button = QPushButton("Add layer to project")
        self.metadata_button = QPushButton("View metadata")
        self.load_button.setEnabled(False)
        self.metadata_button.setEnabled(False)

        self._build_ui()
        self._wire_events()
        self.load_catalog()

    def _build_ui(self):
        self.filter_input.setPlaceholderText("Filter institutions by name...")
        self.layer_filter_input.setPlaceholderText("Filter layers by name...")

        for service_type in ("wms", "wfs", "wcs"):
            handler = self.handlers[service_type]
            service_list = QListWidget()
            self.service_widgets[service_type] = service_list

            page_layout = QVBoxLayout()
            page_layout.addWidget(service_list)
            container = QDialog()
            container.setLayout(page_layout)
            self.tabs.addTab(container, handler.tab_name)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Institutions"))
        left_layout.addWidget(self.filter_input)
        left_layout.addWidget(self.tabs)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Available layers"))
        right_layout.addWidget(self.layer_filter_input)
        right_layout.addWidget(self.layer_list)
        right_layout.addWidget(QLabel("Format (WFS only):"))
        right_layout.addWidget(self.format_combo)
        right_layout.addWidget(self.metadata_button)
        right_layout.addWidget(self.load_button)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)
        self.setLayout(main_layout)

    def _wire_events(self):
        for service_type, widget in self.service_widgets.items():
            widget.itemSelectionChanged.connect(
                lambda current_service_type=service_type: self.show_layers(current_service_type)
            )
        self.filter_input.textChanged.connect(self.apply_catalog_filter)
        self.layer_filter_input.textChanged.connect(self.apply_layer_filter)
        self.layer_list.itemSelectionChanged.connect(self.update_load_button)
        self.layer_list.itemDoubleClicked.connect(self.on_layer_double_clicked)
        self.metadata_button.clicked.connect(self.open_metadata)
        self.load_button.clicked.connect(self.add_layer)

    def load_catalog(self):
        try:
            self.catalog = fetch_catalog()
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Cannot fetch catalog: {error}")
            return

        self.apply_catalog_filter()

    def apply_catalog_filter(self):
        filter_text = self._normalize_filter_text(self.filter_input.text())

        for widget in self.service_widgets.values():
            widget.clear()

        for entry in self.catalog:
            description = entry.get("descricao", entry.get("url", ""))
            normalized_description = self._normalize_filter_text(description)
            if filter_text and filter_text not in normalized_description:
                continue

            for service_type, handler in self.handlers.items():
                if entry.get(handler.availability_key):
                    item = QListWidgetItem(description)
                    item.setData(Qt.UserRole, entry)
                    self.service_widgets[service_type].addItem(item)

        self.layer_list.clear()
        self.current_layers = []
        self.load_button.setEnabled(False)
        self.metadata_button.setEnabled(False)

    def show_layers(self, service_type):
        self.current_service_type = service_type
        self.layer_list.clear()
        self.current_layers = []
        self.load_button.setEnabled(False)
        self.metadata_button.setEnabled(False)
        self.format_combo.setEnabled(service_type == "wfs")

        selected_service = self.service_widgets[service_type].currentItem()
        if not selected_service:
            return

        entry = selected_service.data(Qt.UserRole)
        handler = self.handlers[service_type]

        progress = QProgressDialog(
            "Carregando GetCapabilities. Isso pode levar alguns segundos...",
            "",
            0,
            100,
            self,
        )
        progress.setWindowTitle("Aguarde")
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        try:
            layers = handler.list_layers(entry)
            progress.setValue(70)
            QApplication.processEvents()
        except Exception as error:
            QMessageBox.warning(self, "Error", f"Failed to parse capabilities: {error}")
            layers = []
        finally:
            progress.setValue(100)
            progress.close()

        for layer in layers:
            layer_name, layer_title, metadata_url = self._normalize_layer_item(layer)
            self.current_layers.append((service_type, entry, layer_name, layer_title, metadata_url))

        self.apply_layer_filter()

    def apply_layer_filter(self):
        filter_text = self._normalize_filter_text(self.layer_filter_input.text())
        self.layer_list.clear()
        self.load_button.setEnabled(False)
        self.metadata_button.setEnabled(False)

        for service_type, entry, layer_name, layer_title, metadata_url in self.current_layers:
            normalized_title = self._normalize_filter_text(layer_title)
            normalized_name = self._normalize_filter_text(layer_name)
            if filter_text and filter_text not in normalized_title and filter_text not in normalized_name:
                continue

            item = QListWidgetItem(layer_title)
            item.setData(Qt.UserRole, (service_type, entry, layer_name, metadata_url))
            self.layer_list.addItem(item)

    def update_load_button(self):
        selected = self.layer_list.currentItem()
        self.load_button.setEnabled(bool(selected))
        metadata_url = self._get_selected_metadata_url()
        self.metadata_button.setEnabled(bool(metadata_url))

    def on_layer_double_clicked(self, item):
        self.layer_list.setCurrentItem(item)
        self.add_layer()

    def add_layer(self):
        selected_layer = self.layer_list.currentItem()
        if not selected_layer:
            return

        service_type, entry, layer_name, _ = selected_layer.data(Qt.UserRole)
        if service_type != self.current_service_type:
            service_type = self.current_service_type

        handler = self.handlers.get(service_type)
        if not handler:
            QMessageBox.warning(self, "Error", f"Unsupported service type: {service_type}")
            return

        try:
            layer = handler.create_layer(
                entry=entry,
                layer_name=layer_name,
                options={"format_text": self.format_combo.currentText()},
                parent=self,
            )
            if layer and layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                QMessageBox.information(self, "Success", f"Layer {layer_name} added")
            else:
                error_message = self._extract_error_message(layer)
                QMessageBox.warning(self, "Error", f"Failed to create layer: {error_message}")
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Exception: {error}")

    def open_metadata(self):
        metadata_url = self._get_selected_metadata_url()
        if not metadata_url:
            QMessageBox.information(
                self,
                "Metadata",
                "No metadata URL is available for this layer.",
            )
            return

        progress = QProgressDialog("Loading metadata...", "", 0, 0, self)
        progress.setWindowTitle("Please wait")
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()

        try:
            summary = fetch_metadata_summary(metadata_url)
            dialog = MetadataSummaryDialog(metadata_url=metadata_url, summary=summary, parent=self)
            dialog.exec_()
        except Exception as error:
            QMessageBox.warning(self, "Error", f"Failed to load metadata: {error}")
        finally:
            progress.close()

    def _get_selected_metadata_url(self):
        selected_layer = self.layer_list.currentItem()
        if not selected_layer:
            return None

        data = selected_layer.data(Qt.UserRole)
        if not data:
            return None

        if len(data) >= 4:
            return data[3]
        return None

    @staticmethod
    def _normalize_layer_item(layer):
        if isinstance(layer, (list, tuple)):
            if len(layer) >= 3:
                return layer[0], layer[1], layer[2]
            if len(layer) == 2:
                return layer[0], layer[1], None
        return str(layer), str(layer), None

    @staticmethod
    def _normalize_filter_text(value):
        text = (value or "").strip().lower()
        if not text:
            return ""
        return "".join(
            char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn"
        )

    @staticmethod
    def _extract_error_message(layer):
        error_message = "Layer is invalid."
        if not layer:
            return error_message

        if hasattr(layer, "error") and callable(layer.error):
            error_obj = layer.error()
            if hasattr(error_obj, "summary"):
                error_message = error_obj.summary()
            elif hasattr(error_obj, "message"):
                error_message = error_obj.message()
            else:
                error_message = str(error_obj)
        return error_message
