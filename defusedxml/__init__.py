"""Small vendored compatibility layer for safe XML parsing.

The QGIS plugin repository scanner expects code that parses untrusted XML to
use defusedxml-style APIs. Some QGIS Python installations do not ship the
external ``defusedxml`` package, so this plugin carries the tiny subset it
needs: ``defusedxml.ElementTree.fromstring`` and the related exceptions.
"""

