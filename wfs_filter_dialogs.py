# -*- coding: utf-8 -*-
"""Dialogs used to build spatial filters for WFS requests."""

import html

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsOgcUtils,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsWkbTypes,
)
from qgis.gui import QgsMapCanvas, QgsMapTool, QgsRubberBand
from .wfs_attribute_filter import attribute_filter, TEXT_OPERATORS, NUMBER_OPERATORS


class AttributeFilterDialog(QDialog):
    """Edit one typed attribute condition."""

    def __init__(self, fields, initial=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Filtro por atributo')
        self.resize(460, 180)
        self.field_combo = QComboBox()
        for name, kind in fields:
            self.field_combo.addItem(name, kind)
        self.operator_combo = QComboBox()
        self.value_input = QLineEdit()
        self.operator_combo.currentIndexChanged.connect(self._update_value_hint)
        self.value_input.setPlaceholderText('Ex.: Brasília ou 100000 (sem separador de milhares)')
        self.field_combo.currentIndexChanged.connect(self._update_operators)
        self._update_operators()
        if initial:
            field, operator, value = initial
            self.field_combo.setCurrentIndex(max(0, self.field_combo.findText(field)))
            self.operator_combo.setCurrentIndex(max(0, self.operator_combo.findData(operator)))
            self.value_input.setText(value)
        form = QFormLayout()
        form.addRow('Campo:', self.field_combo)
        form.addRow('Operador:', self.operator_combo)
        form.addRow('Valor:', self.value_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _update_operators(self):
        self.operator_combo.clear()
        for label, code in (TEXT_OPERATORS if self.field_combo.currentData() == 'text' else NUMBER_OPERATORS):
            self.operator_combo.addItem(label, code)

    def condition(self):
        return (self.field_combo.currentText(), self.operator_combo.currentData(), self.value_input.text())

    def _update_value_hint(self):
        is_in = self.operator_combo.currentData() == 'in'
        self.value_input.setPlaceholderText(
            "Ex.: 'RJ', 'ES', 'MG'" if is_in else 'Ex.: Brasília ou 100000 (sem separador de milhares)')
        self.value_input.setToolTip(
            "Separe os valores por vírgulas. Use aspas para valores com vírgulas; "
            "duplique apóstrofos internos: 'D''Ávila'." if is_in else '')

    def filter_text(self):
        field, operator, value = self.condition()
        return attribute_filter(field, self.field_combo.currentData(), operator, value)

    def _accept_if_valid(self):
        try:
            self.filter_text()
        except ValueError as error:
            QMessageBox.warning(self, 'Filtro por atributo', str(error))
            return
        self.accept()


class RectangleMapTool(QgsMapTool):
    """Map tool that creates a rectangle by dragging over the canvas."""

    def __init__(self, canvas, callback):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self.start_point = None
        self.rubber_band = QgsRubberBand(
            canvas, QgsWkbTypes.GeometryType.PolygonGeometry
        )
        self.rubber_band.setColor(QColor(0, 120, 255, 90))
        self.rubber_band.setStrokeColor(QColor(0, 100, 230))
        self.rubber_band.setWidth(2)

    def canvasPressEvent(self, event):
        self.start_point = self.toMapCoordinates(event.pos())
        self.rubber_band.reset(QgsWkbTypes.GeometryType.PolygonGeometry)

    def canvasMoveEvent(self, event):
        if self.start_point is not None:
            self._show_rectangle(self.toMapCoordinates(event.pos()))

    def canvasReleaseEvent(self, event):
        if self.start_point is None:
            return
        end_point = self.toMapCoordinates(event.pos())
        rectangle = QgsRectangle(self.start_point, end_point)
        self._show_rectangle(end_point)
        self.start_point = None
        if not rectangle.isEmpty():
            self.callback(rectangle)

    def _show_rectangle(self, end_point):
        rectangle = QgsRectangle(self.start_point, end_point)
        points = [
            QgsPointXY(rectangle.xMinimum(), rectangle.yMinimum()),
            QgsPointXY(rectangle.xMaximum(), rectangle.yMinimum()),
            QgsPointXY(rectangle.xMaximum(), rectangle.yMaximum()),
            QgsPointXY(rectangle.xMinimum(), rectangle.yMaximum()),
        ]
        self.rubber_band.setToGeometry(QgsGeometry.fromPolygonXY([points]), None)


class BboxMapDialog(QDialog):
    """Select a WGS 84 bounding box on an OpenStreetMap base map."""

    def __init__(self, initial_bbox="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Desenhar retângulo envolvente (BBOX)")
        self.resize(900, 600)
        self._bbox = None

        self.canvas = QgsMapCanvas(self)
        self.canvas.setCanvasColor(Qt.GlobalColor.white)
        self.canvas.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        base_layer = QgsRasterLayer(
            "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmax=19&zmin=0",
            "OpenStreetMap",
            "wms",
        )
        if base_layer.isValid():
            self.canvas.setLayers([base_layer])
            self._base_layer = base_layer
        self.canvas.setExtent(QgsRectangle(-8200000, -4400000, -3800000, 650000))

        help_label = QLabel("Clique, arraste e solte no mapa para delimitar a área desejada.")
        help_label.setWordWrap(True)
        self.value_label = QLabel("Nenhum retângulo desenhado.")
        self.value_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        clear_button = QPushButton("Limpar retângulo")
        clear_button.clicked.connect(self._clear)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.value_label)
        layout.addWidget(clear_button)
        layout.addWidget(buttons)

        self.map_tool = RectangleMapTool(self.canvas, self._rectangle_selected)
        self.canvas.setMapTool(self.map_tool)
        if initial_bbox:
            self._load_initial_bbox(initial_bbox)

    def _rectangle_selected(self, rectangle):
        transform = QgsCoordinateTransform(
            self.canvas.mapSettings().destinationCrs(),
            QgsCoordinateReferenceSystem("EPSG:4326"),
            QgsProject.instance(),
        )
        self._bbox = transform.transformBoundingBox(rectangle)
        self.value_label.setText(self.bbox_text())

    def _load_initial_bbox(self, value):
        try:
            parts = [part.strip() for part in value.split(",")]
            rectangle = QgsRectangle(*[float(part) for part in parts[:4]])
            transform = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem(parts[4] if len(parts) == 5 else "EPSG:4326"),
                self.canvas.mapSettings().destinationCrs(),
                QgsProject.instance(),
            )
            canvas_rectangle = transform.transformBoundingBox(rectangle)
            self.canvas.setExtent(canvas_rectangle)
            self.canvas.refresh()
            self.map_tool.start_point = QgsPointXY(canvas_rectangle.xMinimum(), canvas_rectangle.yMinimum())
            self.map_tool._show_rectangle(QgsPointXY(canvas_rectangle.xMaximum(), canvas_rectangle.yMaximum()))
            self.map_tool.start_point = None
            self._bbox = rectangle
            self.value_label.setText(self.bbox_text())
        except (TypeError, ValueError):
            pass

    def _clear(self):
        self._bbox = None
        self.map_tool.rubber_band.reset(QgsWkbTypes.GeometryType.PolygonGeometry)
        self.value_label.setText("Nenhum retângulo desenhado.")

    def _accept_if_valid(self):
        if self._bbox is None:
            QMessageBox.information(self, "BBOX", "Desenhe um retângulo no mapa antes de continuar.")
            return
        self.accept()

    def bbox_text(self):
        if self._bbox is None:
            return ""
        return "{:.8f},{:.8f},{:.8f},{:.8f},EPSG:4326".format(
            self._bbox.xMinimum(), self._bbox.yMinimum(),
            self._bbox.xMaximum(), self._bbox.yMaximum(),
        )


class SpatialFilterDialog(QDialog):
    """Build an OGC Filter Encoding 2.0 spatial predicate from WKT."""

    def __init__(self, initial_filter="", geometry_property="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Criar filtro espacial avançado")
        self.resize(650, 520)

        self.operator_combo = QComboBox()
        self.operator_combo.addItems(
            ["Intersects", "Within", "Contains", "Disjoint", "Touches", "Crosses", "Overlaps"]
        )
        self.geometry_property = QLineEdit(geometry_property)
        self.geometry_property.setPlaceholderText("Ex.: geom ou the_geom")
        self.crs_input = QLineEdit("EPSG:4326")
        self.wkt_input = QTextEdit()
        self.wkt_input.setPlaceholderText(
            "Ex.: POLYGON((-48 -16, -46 -16, -46 -14, -48 -14, -48 -16))"
        )
        self.filter_output = QTextEdit()
        self.filter_output.setReadOnly(True)
        self.filter_output.setPlainText(initial_filter)

        form = QFormLayout()
        form.addRow("Relação espacial:", self.operator_combo)
        form.addRow("Propriedade geométrica:", self.geometry_property)
        form.addRow("CRS:", self.crs_input)
        form.addRow("Geometria (WKT):", self.wkt_input)
        generate_button = QPushButton("Gerar Filter Encoding")
        generate_button.clicked.connect(self._generate)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(generate_button)
        layout.addWidget(QLabel("Filter Encoding gerado:"))
        layout.addWidget(self.filter_output, 1)
        layout.addWidget(buttons)

    def _generate(self):
        geometry = QgsGeometry.fromWkt(self.wkt_input.toPlainText().strip())
        if geometry.isNull() or geometry.isEmpty():
            QMessageBox.warning(self, "Filtro espacial", "Informe uma geometria WKT válida.")
            return
        property_name = self.geometry_property.text().strip()
        crs = self.crs_input.text().strip()
        if not property_name or not crs:
            QMessageBox.warning(self, "Filtro espacial", "Informe a propriedade geométrica e o CRS.")
            return
        document = QDomDocument()
        gml_element = QgsOgcUtils.geometryToGML(
            geometry,
            document,
            QgsOgcUtils.GMLVersion.GML_3_2_1,
            crs,
            False,
            "spatial-filter",
            8,
        )
        if gml_element.isNull():
            QMessageBox.warning(self, "Filtro espacial", "Não foi possível converter a geometria para GML.")
            return
        document.appendChild(gml_element)
        gml = document.toString(-1)
        operator = self.operator_combo.currentText()
        self.filter_output.setPlainText(
            '<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0" '
            'xmlns:gml="http://www.opengis.net/gml/3.2">'
            '<fes:{0}><fes:ValueReference>{1}</fes:ValueReference>{2}'
            '</fes:{0}></fes:Filter>'.format(
                operator, html.escape(property_name, quote=True), gml
            )
        )

    def _accept_if_valid(self):
        if not self.filter_output.toPlainText().strip():
            self._generate()
        if self.filter_output.toPlainText().strip():
            self.accept()

    def filter_text(self):
        return self.filter_output.toPlainText().strip()
