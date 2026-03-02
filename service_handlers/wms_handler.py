import ssl
import urllib.request

from qgis.core import QgsRasterLayer

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

        context = ssl.create_default_context()
        with urllib.request.urlopen(capabilities_url, context=context, timeout=30) as response:
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
        metadata_url = layer.find("wms:MetadataURL/wms:OnlineResource", namespaces)
        if metadata_url is None:
            return None

        for key in ("{http://www.w3.org/1999/xlink}href", "href"):
            value = metadata_url.get(key)
            if value:
                return value
        return None
