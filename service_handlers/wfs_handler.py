import os
import re
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from qgis.PyQt.QtWidgets import QApplication, QMessageBox
from qgis.core import QgsGeometry, QgsVectorLayer, QgsWkbTypes

from .base import ServiceHandler, parse_xml_safe


class WfsServiceHandler(ServiceHandler):
    service_type = "wfs"
    tab_name = "WFS"
    availability_key = "wfsAvailable"
    capabilities_key = "wfsGetCapabilities"

    FORMAT_MAP = {
        "GML (default)": "application/gml+xml",
        "GML (padrao)": "application/gml+xml",
        "Shapefile (zip)": "shape-zip",
        "JSON": "application/json",
    }

    def list_layers(self, entry):
        capabilities_url = entry.get(self.capabilities_key)
        if not capabilities_url:
            return []

        context = ssl.create_default_context()
        with urllib.request.urlopen(capabilities_url, context=context, timeout=30) as response:
            xml_data = response.read()

        root = parse_xml_safe(xml_data)
        namespaces = [
            {
                "wfs": "http://www.opengis.net/wfs/2.0.0",
                "ows": "http://www.opengis.net/ows/1.1",
            },
            {
                "wfs": "http://www.opengis.net/wfs/2.0",
                "ows": "http://www.opengis.net/ows/1.1",
            },
            {
                "wfs": "http://www.opengis.net/wfs",
                "ows": "http://www.opengis.net/ows",
            },
        ]

        feature_types = []
        default_metadata_url = self._extract_entry_metadata_url(entry)
        for namespace in namespaces:
            for feature_type in root.findall(".//wfs:FeatureType", namespace):
                name = feature_type.find("wfs:Name", namespace)
                title = feature_type.find("wfs:Title", namespace)
                if name is not None and name.text:
                    layer_title = title.text if title is not None else name.text
                    metadata_url = self._extract_feature_metadata_url(feature_type, namespace)
                    # normalise the URL immediately so downstream code doesn't need
                    # to remember to fix it again
                    from ..metadata_viewer import _prepare_metadata_url
                    metadata_url = _prepare_metadata_url(metadata_url) if metadata_url else metadata_url
                    feature_types.append((name.text, layer_title, metadata_url or default_metadata_url))
            if feature_types:
                return feature_types

        for feature_type in root.findall(".//FeatureType"):
            name = feature_type.find("Name")
            title = feature_type.find("Title")
            if name is not None and name.text:
                layer_title = title.text if title is not None else name.text
                metadata_url = self._extract_feature_metadata_url(feature_type)
                from ..metadata_viewer import _prepare_metadata_url
                metadata_url = _prepare_metadata_url(metadata_url) if metadata_url else metadata_url
                feature_types.append((name.text, layer_title, metadata_url or default_metadata_url))
        return feature_types

    def create_layer(self, entry, layer_name, options=None, parent=None):
        service_url = entry.get("url")
        selected_format = (options or {}).get("format_text", "GML (padrao)")
        startindex = (options or {}).get("startindex")
        count = (options or {}).get("count")
        progress_callback = (options or {}).get("progress_callback")
        output_format = self.FORMAT_MAP.get(selected_format, "application/gml+xml")
        QApplication.processEvents()
        temp_file = self._download_wfs_file(
            service_url,
            layer_name,
            output_format,
            startindex=startindex,
            count=count,
            progress_callback=progress_callback,
        )

        if not temp_file:
            raise Exception("Falha ao baixar dados WFS do servidor.")

        if output_format == "shape-zip":
            return self._load_shapefile(temp_file, layer_name, parent)
        if "json" in output_format.lower():
            return self._load_json(temp_file, layer_name)
        return self._load_gml(temp_file, layer_name)

    def _download_wfs_file(
        self,
        url,
        layer_name,
        output_format,
        startindex=None,
        count=None,
        progress_callback=None,
        timeout=60,
    ):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        base_params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": layer_name,
        }
        if startindex is not None:
            base_params["STARTINDEX"] = startindex
        if count is not None:
            base_params["COUNT"] = count

        if "gml" in output_format.lower():
            output_formats = [
                "application/gml+xml",
                "text/xml; subtype=gml/3.2",
                "GML3",
                "gml32",
                None,
            ]
        else:
            output_formats = [output_format]

        data = None
        for current_format in output_formats:
            params_with_srs = dict(base_params)
            params_with_srs["srsName"] = "EPSG:4326"
            if current_format:
                params_with_srs["outputFormat"] = current_format

            request_url = self._build_url(url, params_with_srs)
            data = self._attempt_download(
                request_url,
                context,
                timeout,
                progress_callback=progress_callback,
            )
            if data is not None:
                break

            params_without_srs = dict(base_params)
            if current_format:
                params_without_srs["outputFormat"] = current_format
            retry_url = self._build_url(url, params_without_srs)
            print(f"[WFS] retrying without srsName: {retry_url}")
            data = self._attempt_download(
                retry_url,
                context,
                timeout,
                progress_callback=progress_callback,
            )
            if data is not None:
                break

        if data is None:
            print("[WFS] All download attempts failed")
            return None

        suffix = self._file_suffix_for_format(output_format)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(data)
        temp_file.close()
        print(f"[WFS] Downloaded to {temp_file.name}")
        return temp_file.name

    @staticmethod
    def _build_url(base_url, params):
        query = urllib.parse.urlencode(params, doseq=True)
        return f"{base_url}?{query}"

    @staticmethod
    def _attempt_download(request_url, context, timeout, progress_callback=None):
        try:
            print(f"[WFS] Requesting: {request_url}")
            with urllib.request.urlopen(request_url, context=context, timeout=timeout) as response:
                chunks = []
                bytes_received = 0
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    bytes_received += len(chunk)
                    if callable(progress_callback):
                        progress_callback(bytes_received)
                        QApplication.processEvents()
                return b"".join(chunks)
        except urllib.error.HTTPError as error:
            body_preview = ""
            try:
                body_preview = error.read(300).decode("utf-8", errors="ignore")
            except Exception:
                pass
            print(f"[WFS] HTTP {error.code}: {error.reason}. Body preview: {body_preview}")
            return None
        except Exception as error:
            print(f"[WFS] request error: {error}")
            return None

    @staticmethod
    def _file_suffix_for_format(output_format):
        if output_format == "shape-zip":
            return ".zip"
        if "json" in output_format.lower():
            return ".json"
        return ".gml"

    @staticmethod
    def _extract_feature_metadata_url(feature_type, namespace=None):
        namespace = namespace or {}
        nodes = []

        if namespace:
            nodes.append(feature_type.find("wfs:MetadataURL", namespace))
            nodes.append(feature_type.find("ows:Metadata", namespace))

        nodes.append(feature_type.find("MetadataURL"))
        nodes.append(feature_type.find("Metadata"))

        for node in nodes:
            if node is None:
                continue

            href = node.get("{http://www.w3.org/1999/xlink}href") or node.get("href")
            if href:
                return href

            if node.text and node.text.strip():
                return node.text.strip()

            online_resource = node.find(".//{*}OnlineResource")
            if online_resource is not None:
                href = online_resource.get("{http://www.w3.org/1999/xlink}href") or online_resource.get("href")
                if href:
                    return href
        return None

    @staticmethod
    def _extract_entry_metadata_url(entry):
        for key, value in (entry or {}).items():
            if not isinstance(value, str):
                continue
            lowered_key = str(key).lower()
            if "metadata" in lowered_key or "metadado" in lowered_key:
                if value.startswith("http://") or value.startswith("https://"):
                    return value
        return None

    def _load_shapefile(self, temp_file, layer_name, parent):
        try:
            with zipfile.ZipFile(temp_file, "r") as zipped:
                zipped.extractall(os.path.dirname(temp_file))

            shapefile_path = None
            for filename in os.listdir(os.path.dirname(temp_file)):
                if filename.endswith(".shp"):
                    shapefile_path = os.path.join(os.path.dirname(temp_file), filename)
                    break
            if not shapefile_path:
                raise Exception("Nenhum arquivo .shp encontrado no zip baixado.")

            layer = QgsVectorLayer(shapefile_path, layer_name, "ogr")
            if layer.isValid() and self._should_ask_coordinate_flip(layer):
                answer = QMessageBox.question(
                    parent,
                    "Ordem de coordenadas WFS",
                    "Parece que as coordenadas da camada WFS podem estar invertidas "
                    "(latitude/longitude).\nDeseja inverter?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if answer == QMessageBox.Yes:
                    layer = self._flip_layer_coordinates(layer, layer_name)
            return layer
        except Exception as error:
            raise Exception(f"Falha ao extrair shapefile: {error}")

    @staticmethod
    def _should_ask_coordinate_flip(layer):
        extent = layer.extent()
        return (
            extent.xMinimum() > 90
            or extent.xMaximum() > 90
            or extent.yMinimum() < -90
            or extent.yMaximum() < -90
        )

    def _flip_layer_coordinates(self, layer, layer_name):
        try:
            geometry_type = QgsWkbTypes.geometryType(layer.wkbType())
            geometry_name = {
                0: "Point",
                1: "LineString",
                2: "Polygon",
                3: "MultiPoint",
                4: "MultiLineString",
                5: "MultiPolygon",
            }.get(geometry_type, "Unknown")

            flipped_layer = QgsVectorLayer(
                f"?memory=yes&geometry={geometry_name}",
                f"{layer_name} (flipped)",
                "memory",
            )
            provider = flipped_layer.dataProvider()
            provider.addAttributes(layer.fields())
            flipped_layer.updateFields()

            features = []
            for feature in layer.getFeatures():
                if feature.geometry():
                    wkt = feature.geometry().asWkt()
                    flipped_wkt = self._flip_wkt_coordinates(wkt)
                    flipped_geometry = QgsGeometry.fromWkt(flipped_wkt)
                    if flipped_geometry and not flipped_geometry.isNull():
                        feature.setGeometry(flipped_geometry)
                features.append(feature)

            if features:
                provider.addFeatures(features)

            if layer.crs().isValid():
                flipped_layer.setCrs(layer.crs())
            return flipped_layer
        except Exception as error:
            print(f"[WFS] Error flipping coordinates: {error}")
            return layer

    @staticmethod
    def _flip_wkt_coordinates(wkt):
        pattern = r"([-\d.]+)\s+([-\d.]+)"

        def swap(match):
            x_coord, y_coord = match.groups()
            return f"{y_coord} {x_coord}"

        return re.sub(pattern, swap, wkt)

    @staticmethod
    def _load_json(temp_file, layer_name):
        return QgsVectorLayer(temp_file, layer_name, "ogr")

    @staticmethod
    def _load_gml(temp_file, layer_name):
        layer = QgsVectorLayer(temp_file, layer_name, "ogr")
        if layer.isValid():
            return layer
        uri = f"{temp_file}|geometrytype=auto"
        return QgsVectorLayer(uri, layer_name, "ogr")
