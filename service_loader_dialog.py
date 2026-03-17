# -*- coding: utf-8 -*-
"""
Dialog for browsing INDE catalog and loading WMS/WFS/WCS layers.
"""

from qgis.PyQt.QtCore import QTimer, Qt
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
from qgis.core import QgsNetworkAccessManager, QgsProject
import unicodedata

from .catalog_client import fetch_catalog
from .metadata_viewer import MetadataSummaryDialog, fetch_metadata_summary
from .service_handlers import build_service_handlers


class DownloadSpinnerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aguarde")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumWidth(360)

        self._frames = ["|", "/", "-", "\\"]
        self._frame_index = 0

        self.spinner_label = QLabel(self._frames[0])
        self.spinner_label.setAlignment(Qt.AlignCenter)
        self.spinner_label.setMinimumWidth(18)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)

        layout = QHBoxLayout()
        layout.addWidget(self.spinner_label)
        layout.addWidget(self.message_label, 1)
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self._advance_spinner)

        self.set_downloaded_bytes(0)

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

    def set_downloaded_bytes(self, bytes_received):
        self.message_label.setText(
            f"Baixando dados... ({self._format_bytes(bytes_received)} recebidos)"
        )

    def _advance_spinner(self):
        self._frame_index = (self._frame_index + 1) % len(self._frames)
        self.spinner_label.setText(self._frames[self._frame_index])

    @staticmethod
    def _format_bytes(num_bytes):
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(max(num_bytes, 0))
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        return f"{size:.1f} {units[unit_index]}"


class NetworkDownloadTracker:
    def __init__(self, progress_dialog):
        self.progress_dialog = progress_dialog
        self.network_manager = QgsNetworkAccessManager.instance()
        self.active_request_ids = set()

    def start(self):
        signal_name = self._request_signal_name()
        if signal_name:
            getattr(self.network_manager, signal_name).connect(self._on_request_created)
        self.network_manager.downloadProgress.connect(self._on_download_progress)
        self.network_manager.finished.connect(self._on_request_finished)

    def stop(self):
        signal_name = self._request_signal_name()
        if signal_name:
            try:
                getattr(self.network_manager, signal_name).disconnect(self._on_request_created)
            except TypeError:
                pass
        try:
            self.network_manager.downloadProgress.disconnect(self._on_download_progress)
        except TypeError:
            pass
        try:
            self.network_manager.finished.disconnect(self._on_request_finished)
        except TypeError:
            pass
        self.active_request_ids.clear()

    def _request_signal_name(self):
        if hasattr(self.network_manager, "requestAboutToBeCreated"):
            return "requestAboutToBeCreated"
        if hasattr(self.network_manager, "requestCreated"):
            return "requestCreated"
        return None

    def _on_request_created(self, *args):
        for arg in args:
            try:
                request_url = arg.request().url().toString().lower()
                request_id = arg.requestId()
            except Exception:
                continue

            if any(
                token in request_url
                for token in ("request=getmap", "request=getfeature", "request=getcoverage")
            ):
                self.active_request_ids.add(request_id)
                return

    def _on_download_progress(self, *args):
        if len(args) < 3:
            return
        request_id, bytes_received, _bytes_total = args[:3]
        if self.active_request_ids and request_id not in self.active_request_ids:
            return
        self.progress_dialog.set_downloaded_bytes(bytes_received)
        QApplication.processEvents()

    def _on_request_finished(self, *args):
        reply = args[0] if args else None
        request_id = getattr(reply, "requestId", lambda: None)()
        if request_id in self.active_request_ids:
            self.active_request_ids.discard(request_id)


class ServiceLoaderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Carregador de servicos OGC da INDE")
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
        self.format_combo.addItems(["GML (padrao)", "Shapefile (zip)", "JSON"])
        self.wfs_startindex_input = QLineEdit()
        self.wfs_count_input = QLineEdit()
        self.load_button = QPushButton("Adicionar camada ao projeto")
        self.metadata_button = QPushButton("Ver metadados")
        self.load_button.setEnabled(False)
        self.metadata_button.setEnabled(False)
        self.wfs_startindex_input.setEnabled(False)
        self.wfs_count_input.setEnabled(False)

        self._build_ui()
        self._wire_events()
        self.load_catalog()

    def _build_ui(self):
        self.filter_input.setPlaceholderText("Filtrar instituicoes por nome...")
        self.layer_filter_input.setPlaceholderText("Filtrar camadas por nome...")
        self.wfs_startindex_input.setPlaceholderText("Ex.: 0")
        self.wfs_count_input.setPlaceholderText("Ex.: 100")

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
        left_layout.addWidget(QLabel("Instituicoes"))
        left_layout.addWidget(self.filter_input)
        left_layout.addWidget(self.tabs)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Camadas disponiveis"))
        right_layout.addWidget(self.layer_filter_input)
        right_layout.addWidget(self.layer_list)
        right_layout.addWidget(QLabel("Formato (apenas WFS):"))
        right_layout.addWidget(self.format_combo)
        right_layout.addWidget(QLabel("STARTINDEX (WFS 2.0 - opcional):"))
        right_layout.addWidget(self.wfs_startindex_input)
        right_layout.addWidget(QLabel("COUNT (WFS 2.0 - opcional):"))
        right_layout.addWidget(self.wfs_count_input)
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
            QMessageBox.critical(self, "Erro", f"Nao foi possivel carregar o catalogo: {error}")
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
        self.wfs_startindex_input.setEnabled(service_type == "wfs")
        self.wfs_count_input.setEnabled(service_type == "wfs")

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
            QMessageBox.warning(self, "Erro", f"Falha ao processar o capabilities: {error}")
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
            QMessageBox.warning(self, "Erro", f"Tipo de servico nao suportado: {service_type}")
            return

        startindex = self._parse_optional_int(
            self.wfs_startindex_input.text(),
            "STARTINDEX",
            minimum=0,
        )
        count = self._parse_optional_int(
            self.wfs_count_input.text(),
            "COUNT",
            minimum=1,
        )
        if startindex is None and self.wfs_startindex_input.text().strip():
            return
        if count is None and self.wfs_count_input.text().strip():
            return

        progress = DownloadSpinnerDialog(self)
        network_tracker = NetworkDownloadTracker(progress)
        network_tracker.start()
        progress.show()
        QApplication.processEvents()

        try:
            layer = handler.create_layer(
                entry=entry,
                layer_name=layer_name,
                options={
                    "format_text": self.format_combo.currentText(),
                    "startindex": startindex,
                    "count": count,
                    "progress_callback": progress.set_downloaded_bytes,
                },
                parent=self,
            )
            if layer and layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                QMessageBox.information(self, "Sucesso", f"Camada {layer_name} adicionada")
            else:
                error_message = self._extract_error_message(layer)
                QMessageBox.warning(self, "Erro", f"Falha ao criar a camada: {error_message}")
        except Exception as error:
            QMessageBox.critical(self, "Erro", f"Excecao: {error}")
        finally:
            network_tracker.stop()
            progress.close()

    def open_metadata(self):
        metadata_url = self._get_selected_metadata_url()
        if not metadata_url:
            QMessageBox.information(
                self,
                "Metadados",
                "Nao ha URL de metadados disponivel para esta camada.",
            )
            return

        progress = QProgressDialog("Carregando metadados...", "", 0, 0, self)
        progress.setWindowTitle("Aguarde")
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
            QMessageBox.warning(self, "Erro", f"Falha ao carregar metadados: {error}")
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
        error_message = "Camada invalida."
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

    def _parse_optional_int(self, raw_value, label, minimum=0):
        value = (raw_value or "").strip()
        if not value:
            return None
        try:
            parsed = int(value)
        except ValueError:
            QMessageBox.warning(self, "Erro", f"{label} deve ser um numero inteiro.")
            return None
        if parsed < minimum:
            QMessageBox.warning(self, "Erro", f"{label} deve ser maior ou igual a {minimum}.")
            return None
        return parsed
