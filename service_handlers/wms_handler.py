from qgis.core import QgsRasterLayer

from ..network_utils import urlopen
from .base import ServiceHandler, parse_xml_safe


class WmsServiceHandler(ServiceHandler):
    service_type = "wms"
    tab_name = "WMS"
    availability_key = "wmsAvailable"
    capabilities_key = "wmsGetCapabilities"

    def list_layers(self, entry):
        capabilities_url = entry.get(self.capabilities_key)
        if not capabilities_url:
            return []

        with urlopen(capabilities_url, timeout=30) as response:
            xml_data = response.read()

        root = parse_xml_safe(xml_data)
        namespaces = {"wms": "http://www.opengis.net/wms"}
        layers = []
        for layer in root.findall(".//wms:Layer/wms:Layer", namespaces):
            name = layer.find("wms:Name", namespaces)
            title = layer.find("wms:Title", namespaces)
            if name is not None and name.text:
                layer_title = title.text if title is not None else name.text
                metadata_url = self._extract_metadata_url(layer, namespaces)
                # ensure CSW-style URLs include an outputSchema where appropriate
                from ..metadata_viewer import _prepare_metadata_url
                metadata_url = _prepare_metadata_url(metadata_url) if metadata_url else metadata_url
                layers.append((name.text, layer_title, metadata_url))
        return layers

    def create_layer(self, entry, layer_name, options=None, parent=None):
        service_url = entry.get("url")
        uri = (
            f"url={service_url}?service=WMS&request=GetMap&layers={layer_name}"
            "&styles=&format=image/png&crs=EPSG:3857"
        )
        return QgsRasterLayer(uri, layer_name, "wms")

    @staticmethod
    def _extract_metadata_url(layer, namespaces):
        candidates = []
        metadata_nodes = layer.findall("wms:MetadataURL", namespaces)

        for metadata_node in metadata_nodes:
            online_resource = metadata_node.find("wms:OnlineResource", namespaces)
            if online_resource is None:
                continue

            href = None
            for key in ("{http://www.w3.org/1999/xlink}href", "href"):
                value = online_resource.get(key)
                if value:
                    href = value
                    break
            if not href:
                continue

            format_node = metadata_node.find("wms:Format", namespaces)
            format_value = (format_node.text or "").strip().lower() if format_node is not None else ""

            from ..metadata_viewer import _prepare_metadata_url

            normalized = _prepare_metadata_url(href)
            lowered = normalized.lower()
            score = 0
            if "xml" in format_value:
                score += 3
            if "getrecordbyid" in lowered:
                score += 2
            if "service=csw" in lowered:
                score += 1
            candidates.append((score, normalized))

        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            return candidates[0][1]
        return None
