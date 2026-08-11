import os
import re
import tempfile
import urllib.error
import urllib.parse
import zipfile

from ..defusedxml import ElementTree as ET

from qgis.PyQt.QtWidgets import QApplication, QMessageBox
from qgis.core import QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry, QgsVectorLayer, QgsWkbTypes

from ..network_utils import create_ssl_context, urlopen
from .base import ServiceHandler, parse_xml_safe


class WfsServiceHandler(ServiceHandler):
    service_type = "wfs"
    tab_name = "WFS"
    availability_key = "wfsAvalaible"
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

        with urlopen(capabilities_url, timeout=30) as response:
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
        bbox = (options or {}).get("bbox")
        filter_encoding = (options or {}).get("filter_encoding")
        progress_callback = (options or {}).get("progress_callback")
        feature_progress_callback = (options or {}).get("feature_progress_callback")
        feature_count = (options or {}).get("feature_count")
        requested_output_format = self.FORMAT_MAP.get(selected_format, "application/gml+xml")
        output_format = self._effective_output_format(requested_output_format)
        effective_count = feature_count
        if effective_count is None:
            effective_count = self._resolve_effective_count(
                service_url, layer_name, startindex, count, bbox, filter_encoding
            )
        QApplication.processEvents()
        if effective_count > 5000:
            return self._create_paginated_layer(
                service_url,
                layer_name,
                output_format,
                effective_count,
                startindex=startindex,
                bbox=bbox,
                filter_encoding=filter_encoding,
                progress_callback=progress_callback,
                feature_progress_callback=feature_progress_callback,
                parent=parent,
            )

        temp_file, fallback_crs_authid = self._download_wfs_file(
            service_url,
            layer_name,
            output_format,
            startindex=startindex,
            count=count,
            bbox=bbox,
            filter_encoding=filter_encoding,
            progress_callback=progress_callback,
        )

        if not temp_file:
            raise Exception("Falha ao baixar dados WFS do servidor.")

        if output_format == "shape-zip":
            return self._load_shapefile(temp_file, layer_name, parent, fallback_crs_authid)
        if "json" in output_format.lower():
            return self._load_json(temp_file, layer_name, fallback_crs_authid)
        return self._load_gml(temp_file, layer_name, fallback_crs_authid)

    def get_feature_count(
        self, entry, layer_name, startindex=None, count=None, bbox=None, filter_encoding=None
    ):
        service_url = entry.get("url")
        return self._resolve_effective_count(
            service_url, layer_name, startindex, count, bbox, filter_encoding
        )

    def get_geometry_property(self, entry, layer_name, timeout=30):
        """Return the geometry property declared by DescribeFeatureType."""
        service_url = entry.get("url")
        if not service_url:
            return None
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "DescribeFeatureType",
            "typeNames": layer_name,
        }
        request_url = self._build_url(service_url, params)
        context = create_ssl_context()
        with urlopen(request_url, context=context, timeout=timeout) as response:
            return self._parse_geometry_property(response.read())

    @staticmethod
    def _parse_geometry_property(xml_data):
        try:
            root = parse_xml_safe(xml_data)
        except ET.ParseError:
            return None

        for element in root.iter():
            if element.tag.split("}", 1)[-1] != "element":
                continue
            property_type = (element.get("type") or "").lower()
            property_name = element.get("name")
            if property_name and (
                "geometrypropertytype" in property_type
                or "pointpropertytype" in property_type
                or "curvepropertytype" in property_type
                or "linestringpropertytype" in property_type
                or "surfacepropertytype" in property_type
                or "polygonpropertytype" in property_type
                or "multigeometrypropertytype" in property_type
                or "multipointpropertytype" in property_type
                or "multicurvepropertytype" in property_type
                or "multilinestringpropertytype" in property_type
                or "multisurfacepropertytype" in property_type
                or "multipolygonpropertytype" in property_type
            ):
                return property_name
        return None

    def _resolve_effective_count(
        self, service_url, layer_name, startindex=None, count=None, bbox=None, filter_encoding=None
    ):
        if startindex is not None and count is not None:
            return max(0, count)

        total_count = self._fetch_feature_count(
            service_url, layer_name, bbox=bbox, filter_encoding=filter_encoding
        )
        if total_count is None:
            raise Exception("Nao foi possivel determinar a quantidade de feicoes da camada.")

        initial_index = startindex or 0
        if initial_index >= total_count:
            return 0
        remaining = total_count - initial_index
        if count is None:
            return remaining
        return max(0, min(remaining, count))

    def _fetch_feature_count(
        self, url, layer_name, bbox=None, filter_encoding=None, timeout=30
    ):
        context = create_ssl_context()
        base_params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": layer_name,
            "resultType": "hits",
        }
        if bbox:
            base_params["BBOX"] = bbox
        if filter_encoding:
            base_params["FILTER"] = filter_encoding

        for include_srs in (True, False):
            params = dict(base_params)
            if include_srs:
                params["srsName"] = "EPSG:4326"
            request_url = self._build_url(url, params)
            try:
                with urlopen(request_url, context=context, timeout=timeout) as response:
                    xml_data = response.read()
                feature_count = self._parse_feature_count(xml_data)
                if feature_count is not None:
                    return feature_count
            except Exception as error:
                print(f"[WFS] count request error: {error}")
        return None

    @staticmethod
    def _parse_feature_count(xml_data):
        try:
            root = parse_xml_safe(xml_data)
        except ET.ParseError as error:
            print(f"[WFS] count parse error: {error}")
            return None

        for attr_name, attr_value in root.attrib.items():
            local_name = attr_name.split("}", 1)[-1]
            if local_name in ("numberMatched", "numberOfFeatures"):
                if attr_value == "unknown":
                    return None
                try:
                    return int(attr_value)
                except (TypeError, ValueError):
                    continue
        return None

    def _create_paginated_layer(
        self,
        service_url,
        layer_name,
        output_format,
        total_features,
        startindex=None,
        bbox=None,
        filter_encoding=None,
        progress_callback=None,
        feature_progress_callback=None,
        parent=None,
    ):
        chunk_size = 5000
        initial_index = startindex or 0
        downloaded_features = 0
        downloaded_bytes = 0
        merged_layer = None

        while downloaded_features < total_features:
            current_count = min(chunk_size, total_features - downloaded_features)
            current_start = initial_index + downloaded_features
            current_chunk_bytes = {"value": 0}

            def chunk_progress_callback(bytes_received):
                current_chunk_bytes["value"] = max(bytes_received, 0)
                if callable(progress_callback):
                    progress_callback(downloaded_bytes + current_chunk_bytes["value"])

            temp_file, fallback_crs_authid = self._download_wfs_file(
                service_url,
                layer_name,
                output_format,
                startindex=current_start,
                count=current_count,
                bbox=bbox,
                filter_encoding=filter_encoding,
                progress_callback=chunk_progress_callback,
            )
            if not temp_file:
                raise Exception("Falha ao baixar um dos blocos de dados WFS.")

            current_layer = self._load_downloaded_layer(
                temp_file,
                layer_name,
                output_format,
                fallback_crs_authid,
                parent,
            )
            if not current_layer or not current_layer.isValid():
                raise Exception("Falha ao carregar um dos blocos de dados WFS.")

            if merged_layer is None:
                merged_layer = self._create_memory_layer_from_source(current_layer, layer_name)
            self._append_features(merged_layer, current_layer)

            downloaded_bytes += current_chunk_bytes["value"]
            downloaded_features += current_layer.featureCount() or current_count
            if callable(feature_progress_callback):
                feature_progress_callback(min(downloaded_features, total_features), total_features)
                QApplication.processEvents()

        return merged_layer

    def _download_wfs_file(
        self,
        url,
        layer_name,
        output_format,
        startindex=None,
        count=None,
        bbox=None,
        filter_encoding=None,
        progress_callback=None,
        timeout=60,
    ):
        context = create_ssl_context()

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
        if bbox:
            base_params["BBOX"] = bbox
        if filter_encoding:
            base_params["FILTER"] = filter_encoding

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
        fallback_crs_authid = None
        preferred_srs_name = self._preferred_srs_name(output_format)
        for current_format in output_formats:
            params_with_srs = dict(base_params)
            if preferred_srs_name:
                params_with_srs["srsName"] = preferred_srs_name
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
                fallback_crs_authid = "EPSG:4326"
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
            return None, None

        suffix = self._file_suffix_for_format(output_format)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(data)
        temp_file.close()
        print(f"[WFS] Downloaded to {temp_file.name}")
        return temp_file.name, fallback_crs_authid

    @staticmethod
    def _preferred_srs_name(output_format):
        if output_format == "shape-zip":
            return None
        return "EPSG:4326"

    @staticmethod
    def _effective_output_format(output_format):
        if output_format == "shape-zip":
            # Some INDE services swap axes in shapefile exports while GeoJSON
            # loads correctly in QGIS, so prefer GeoJSON for project loading.
            return "application/json"
        return output_format

    @staticmethod
    def _build_url(base_url, params):
        query = urllib.parse.urlencode(params, doseq=True)
        return f"{base_url}?{query}"

    @staticmethod
    def _attempt_download(request_url, context, timeout, progress_callback=None):
        try:
            print(f"[WFS] Requesting: {request_url}")
            with urlopen(request_url, context=context, timeout=timeout) as response:
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
            except (AttributeError, OSError, ValueError):
                body_preview = "<response body unavailable>"
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

    def _load_shapefile(self, temp_file, layer_name, parent, fallback_crs_authid=None):
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
            layer = self._apply_fallback_crs(layer, fallback_crs_authid)
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

    def _load_downloaded_layer(self, temp_file, layer_name, output_format, fallback_crs_authid, parent):
        if "json" in output_format.lower():
            return self._load_json(temp_file, layer_name, fallback_crs_authid)
        return self._load_gml(temp_file, layer_name, fallback_crs_authid)

    @staticmethod
    def _create_memory_layer_from_source(source_layer, layer_name):
        geometry_type = QgsWkbTypes.displayString(source_layer.wkbType()) or "None"
        crs_authid = source_layer.crs().authid() if source_layer.crs().isValid() else ""
        uri = geometry_type
        if crs_authid:
            uri = f"{uri}?crs={crs_authid}"
        memory_layer = QgsVectorLayer(uri, layer_name, "memory")
        provider = memory_layer.dataProvider()
        provider.addAttributes(list(source_layer.fields()))
        memory_layer.updateFields()
        if crs_authid and not memory_layer.crs().isValid():
            memory_layer.setCrs(QgsCoordinateReferenceSystem(crs_authid))
        return memory_layer

    @staticmethod
    def _append_features(target_layer, source_layer):
        provider = target_layer.dataProvider()
        target_fields = target_layer.fields()
        features = []
        for source_feature in source_layer.getFeatures():
            feature = QgsFeature(target_fields)
            feature.setAttributes(source_feature.attributes())
            if source_feature.hasGeometry():
                feature.setGeometry(source_feature.geometry())
            features.append(feature)

        if features:
            provider.addFeatures(features)
            target_layer.updateExtents()

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
    def _load_json(temp_file, layer_name, fallback_crs_authid=None):
        layer = QgsVectorLayer(temp_file, layer_name, "ogr")
        return WfsServiceHandler._apply_fallback_crs(layer, fallback_crs_authid)

    @staticmethod
    def _load_gml(temp_file, layer_name, fallback_crs_authid=None):
        layer = QgsVectorLayer(temp_file, layer_name, "ogr")
        layer = WfsServiceHandler._apply_fallback_crs(layer, fallback_crs_authid)
        if layer.isValid():
            return layer
        uri = f"{temp_file}|geometrytype=auto"
        layer = QgsVectorLayer(uri, layer_name, "ogr")
        return WfsServiceHandler._apply_fallback_crs(layer, fallback_crs_authid)

    @staticmethod
    def _apply_fallback_crs(layer, fallback_crs_authid):
        if not layer or not fallback_crs_authid or not layer.isValid():
            return layer
        if layer.crs().isValid():
            return layer

        fallback_crs = QgsCoordinateReferenceSystem(fallback_crs_authid)
        if fallback_crs.isValid():
            layer.setCrs(fallback_crs)
        return layer
