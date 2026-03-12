# -*- coding: utf-8 -*-
"""
dbdg-inde QGIS plugin implementation.
"""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
import os

# import our dialog
from .service_loader_dialog import ServiceLoaderDialog


class DbdgIndePlugin:
    def __init__(self, iface):
        """Constructor.

        :param iface: A QGIS interface instance.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.action = None

    def initGui(self):
        """Create the menu entries and toolbar icons inside QGIS."""
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.action = QAction(QIcon(icon_path), self.tr("dbdg-inde"), self.iface.mainWindow())
        self.action.setToolTip("serviços DBDG/INDE")
        self.action.setStatusTip("serviços DBDG/INDE")
        self.action.triggered.connect(self.run)
        self.toolbar = self.iface.addToolBar("dbdg-inde")
        self.toolbar.setObjectName('IndeBrasilToolbar')
        self.toolbar.addAction(self.action)


    def unload(self):
        """Removes the plugin menu item and icon."""
        if self.action:
            self.toolbar.removeAction(self.action)

    def run(self):
        """Run method that performs all the real work: show loader dialog."""
        dlg = ServiceLoaderDialog(self.iface.mainWindow())
        dlg.exec_()

    def tr(self, message):
        """Get translation for a string using QGIS translation API."""
        return QCoreApplication.translate("dbdg-inde", message)
