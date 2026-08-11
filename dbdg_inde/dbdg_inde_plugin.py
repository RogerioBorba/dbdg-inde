# -*- coding: utf-8 -*-
"""
dbdg-inde QGIS plugin implementation.
"""

import os

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar

from .service_loader_dialog import ServiceLoaderDialog


class DbdgIndePlugin:
    def __init__(self, iface):
        """Constructor.

        :param iface: A QGIS interface instance.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.action = None
        self.toolbar = None

    def initGui(self):
        """Create the menu entries and toolbar icons inside QGIS."""
        if self.action is not None:
            return

        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.action = QAction(QIcon(icon_path), self.tr("dbdg-inde"), self.iface.mainWindow())
        self.action.setToolTip("servicos DBDG/INDE")
        self.action.setStatusTip("servicos DBDG/INDE")
        self.action.triggered.connect(self.run)

        existing_toolbar = self.iface.mainWindow().findChild(QToolBar, "IndeBrasilToolbar")
        if existing_toolbar is not None:
            self.iface.mainWindow().removeToolBar(existing_toolbar)
            existing_toolbar.deleteLater()

        self.toolbar = self.iface.addToolBar("dbdg-inde")
        self.toolbar.setObjectName("IndeBrasilToolbar")
        self.toolbar.addAction(self.action)

    def unload(self):
        """Removes the plugin menu item and icon."""
        if self.action and self.toolbar:
            self.toolbar.removeAction(self.action)
        if self.action:
            self.action.deleteLater()
            self.action = None
        if self.toolbar:
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None

    def run(self):
        """Run method that performs all the real work: show loader dialog."""
        dlg = ServiceLoaderDialog(self.iface.mainWindow())
        dlg.exec_()

    def tr(self, message):
        """Get translation for a string using QGIS translation API."""
        return QCoreApplication.translate("dbdg-inde", message)
