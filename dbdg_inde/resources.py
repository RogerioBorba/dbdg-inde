# -*- coding: utf-8 -*-
"""
Resource file generated from resources.qrc.
Run

    pyrcc5 -o resources.py resources.qrc

to regenerate if you change the icon or other resources.
"""

from qgis.PyQt.QtGui import QIcon
import os


def get_icon():
    """Return an icon for the plugin (wrapper for consistency)."""
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    return QIcon(icon_path)
