import ssl
import urllib.request

from qgis.core import QgsRasterLayer

from .base import ServiceHandler, parse_xml_safe


class WcsServiceHandler(ServiceHandler):
    service_type = "wcs"
    tab_name = "WCS"
    availability_key = "wcsAvailable"
    capabilities_key = "wcsGetCapabilities"

    def list_layers(self, entry):
        capabilities_url = entry.get(self.capabilities_key)
        if not capabilities_url:
            return []

        context = ssl.create_default_context()
        with urllib.request.urlopen(capabilities_url, context=context, timeout=30) as response:
            xml_data = response.read()

        root = parse_xml_safe(xml_data)
        namespaces = {"wcs": "http://www.opengis.net/wcs/1.1"}
        coverages = []
        for coverage in root.findall(".//wcs:CoverageSummary", namespaces):
            coverage_id = coverage.find("wcs:CoverageId", namespaces)
            if coverage_id is not None and coverage_id.text:
                coverages.append((coverage_id.text, coverage_id.text))
        return coverages

    def create_layer(self, entry, layer_name, options=None, parent=None):
        service_url = entry.get("url")
        uri = f"{service_url}?service=WCS&version=1.1.1&request=GetCoverage&coverage={layer_name}"
        return QgsRasterLayer(uri, layer_name, "wcs")
