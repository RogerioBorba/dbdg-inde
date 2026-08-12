"""Test package setup, including support for relocated OSGeo4W runtimes."""

import os


_osgeo_root = os.environ.get("OSGEO4W_ROOT")
if _osgeo_root and hasattr(os, "add_dll_directory"):
    for _relative_path in (
        "bin",
        os.path.join("apps", "Qt5", "bin"),
        os.path.join("apps", "qgis-ltr", "bin"),
    ):
        _dll_path = os.path.join(_osgeo_root, _relative_path)
        if os.path.isdir(_dll_path):
            os.add_dll_directory(_dll_path)
