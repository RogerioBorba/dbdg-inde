import urllib.parse

from qgis.core import QgsRasterLayer

from ..network_utils import urlopen
from .base import ServiceHandler, extract_wcs_coverages, parse_xml_safe


class WcsServiceHandler(ServiceHandler):
    service_type = "wcs"
    tab_name = "WCS"
    availability_key = "wcsAvailable"
    capabilities_key = "wcsGetCapabilities"

    def list_layers(self, entry):
        capabilities_url = entry.get(self.capabilities_key)
        if not capabilities_url:
            return []

        with urlopen(capabilities_url, timeout=30) as response:
            xml_data = response.read()

        root = parse_xml_safe(xml_data)
        return extract_wcs_coverages(root)

    def create_layer(self, entry, layer_name, options=None, parent=None):
        # Try the native QGIS WCS URI first, then explicit GetCoverage fallbacks
        # for common versions/parameter names.
        layer = None
        for uri in self._build_wcs_uri_candidates(entry, layer_name):
            layer = QgsRasterLayer(uri, layer_name, "wcs")
            if layer and layer.isValid():
                return layer
        return layer

    @staticmethod
    def _build_wcs_uri_candidates(entry, layer_name):
        raw_service_url = (entry or {}).get("url") or ""
        capabilities_url = (entry or {}).get("wcsGetCapabilities") or ""
        coverage_id = urllib.parse.quote(str(layer_name), safe=":_-./")

        base_urls = []
        for raw_url in (raw_service_url, capabilities_url):
            if not raw_url:
                continue
            split = urllib.parse.urlsplit(raw_url)
            clean_base = urllib.parse.urlunsplit((split.scheme, split.netloc, split.path, "", ""))
            if clean_base and clean_base not in base_urls:
                base_urls.append(clean_base)
            if raw_url not in base_urls:
                base_urls.append(raw_url)

        candidates = []
        for base_url in base_urls:
            # Preferred form for QGIS WCS provider.
            candidates.append(f"url={base_url}&identifier={coverage_id}")
            candidates.append(
                f"{base_url}?service=WCS&version=2.0.1&request=GetCoverage&coverageId={coverage_id}"
            )
            candidates.append(
                f"{base_url}?service=WCS&version=1.1.1&request=GetCoverage&identifier={coverage_id}"
            )
            candidates.append(
                f"{base_url}?service=WCS&version=1.0.0&request=GetCoverage&coverage={coverage_id}"
            )
        return candidates
