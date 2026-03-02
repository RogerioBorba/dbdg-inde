# -*- coding: utf-8 -*-
"""
Initialization file for the dbdg-inde QGIS plugin.
This module exposes the required classFactory entry point that QGIS
uses to instantiate the plugin.
"""


def classFactory(iface):
    """Load DbdgIndePlugin class.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    :returns: An instance of the plugin class
    """
    from .dbdg_inde_plugin import DbdgIndePlugin
    return DbdgIndePlugin(iface)
