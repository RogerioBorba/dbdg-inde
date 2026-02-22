import xml.etree.ElementTree as ET
from qgis.core import QgsMessageLog, Qgis, QgsVectorLayer, QgsProject, QgsCoordinateReferenceSystem, QgsRectangle
from qgis.PyQt.QtWidgets import QMessageBox
import requests

class WFSService:
    """Service class to handle WFS operations."""

    NAMESPACES = {
        'wfs': 'http://www.opengis.net/wfs/2.0',
        'wfs1': 'http://www.opengis.net/wfs',
        'ows': 'http://www.opengis.net/ows/1.1',
        'gml': 'http://www.opengis.net/gml/3.2',
        'gml3': 'http://www.opengis.net/gml',
        'xlink': 'http://www.w3.org/1999/xlink',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    }

    @classmethod
    def _get_text(cls, element, paths):
        """Helper method to get text from element using multiple possible paths."""
        if element is None:
            return None
        
        for path in paths:
            try:
                result = element.find(path, cls.NAMESPACES)
                if result is not None and result.text:
                    text = result.text.strip()
                    if text:  # Only return non-empty text
                        return text
            except Exception:
                continue
        
        # If no text found with paths, try to get text from any child element
        for child in element:
            if child.text and child.text.strip():
                return child.text.strip()
                
        return None

    @classmethod
    def _extract_crs(cls, feature_type):
        """Extract CRS information from feature type element."""
        # Try different paths for CRS information
        crs_paths = [
            'DefaultCRS',  # WFS 2.0
            'wfs:DefaultCRS',
            'SRS',        # WFS 1.0
            'wfs:SRS',
            './/DefaultCRS',
            './/SRS'
        ]
        
        crs = cls._get_text(feature_type, crs_paths)
        if not crs:
            return 'EPSG:4326'  # Default to WGS84 if no CRS found
            
        # Handle different CRS URI formats
        if crs.startswith('urn:ogc:def:crs:EPSG::'):
            epsg_code = crs.split(':')[-1]
            # For WFS 2.0, we need to use the complete URN with axis order
            if epsg_code in ['4326', '4674']:  # Geographic coordinate systems
                return f"urn:ogc:def:crs:EPSG::{epsg_code}"
            return f"EPSG:{epsg_code}"
        elif crs.startswith('EPSG:'):
            epsg_code = crs.split(':')[1]
            if epsg_code in ['4326', '4674']:  # Geographic coordinate systems
                return f"urn:ogc:def:crs:EPSG::{epsg_code}"
            return crs
        elif crs.isdigit():
            if crs in ['4326', '4674']:  # Geographic coordinate systems
                return f"urn:ogc:def:crs:EPSG::{crs}"
            return f"EPSG:{crs}"
        else:
            return 'EPSG:4326'  # Default to WGS84 for unrecognized formats

    @classmethod
    def _fix_bbox_coordinates(cls, bbox, crs):
        """
        Corrige a ordem das coordenadas do bbox se necessário.
        Para CRS geográficos (4326, 4674, etc), a ordem deve ser lon,lat.
        """
        if not bbox:
            return bbox
            
        try:
            # Log original coordinates
            QgsMessageLog.logMessage(f"Original bbox coordinates - Lower: {bbox['lower']}, Upper: {bbox['upper']}", "INDE Serviços", level=3)
            
            # Verifica se é um CRS geográfico
            is_geographic = False
            epsg_code = None
            
            if isinstance(crs, str):
                if 'EPSG:' in crs:
                    epsg_code = crs.split(':')[1]
                elif 'urn:ogc:def:crs:EPSG::' in crs:
                    epsg_code = crs.split('::')[1]
                else:
                    epsg_code = crs
                    
                # Lista de CRS geográficos comuns
                geographic_crs = ['4326', '4674', '4618', '4619', '4170']
                is_geographic = epsg_code in geographic_crs
                
            QgsMessageLog.logMessage(f"CRS: {crs}, EPSG code: {epsg_code}, Is geographic: {is_geographic}", "INDE Serviços", level=3)
            
            # Se for CRS geográfico, verifica se precisa inverter
            if is_geographic:
                lower = bbox['lower']
                upper = bbox['upper']
                
                # Converte para float para comparações
                lower_x, lower_y = float(lower[0]), float(lower[1])
                upper_x, upper_y = float(upper[0]), float(upper[1])
                
                # Verifica se as coordenadas parecem estar invertidas usando várias regras:
                needs_swap = False
                
                # Regra 1: Se alguma coordenada X está fora do intervalo de longitude (-180, 180)
                if abs(lower_x) > 180 or abs(upper_x) > 180:
                    needs_swap = True
                    QgsMessageLog.logMessage("Coordenadas X fora do intervalo de longitude", "INDE Serviços", level=3)
                
                # Regra 2: Se as coordenadas X parecem ser latitudes (-90, 90) e as Y longitudes
                elif (abs(lower_x) <= 90 and abs(upper_x) <= 90) and (abs(lower_y) <= 180 and abs(upper_y) <= 180):
                    # Verifica se o padrão parece mais com lat,lon do que lon,lat
                    if abs(lower_y) > 90 or abs(upper_y) > 90:
                        needs_swap = True
                        QgsMessageLog.logMessage("Padrão de coordenadas sugere lat,lon ao invés de lon,lat", "INDE Serviços", level=3)
                
                # Regra 3: Para o Brasil, as longitudes devem estar entre -75 e -30, e latitudes entre -35 e 5
                elif not (-75 <= lower_x <= -30 and -75 <= upper_x <= -30):
                    if -75 <= lower_y <= -30 and -75 <= upper_y <= -30:
                        needs_swap = True
                        QgsMessageLog.logMessage("Coordenadas fora do intervalo esperado para o Brasil", "INDE Serviços", level=3)
                
                if needs_swap:
                    # Inverte as coordenadas
                    bbox['lower'] = [lower[1], lower[0]]
                    bbox['upper'] = [upper[1], upper[0]]
                    QgsMessageLog.logMessage(f"Coordenadas corrigidas - Lower: {bbox['lower']}, Upper: {bbox['upper']}", "INDE Serviços", level=3)
                    
        except Exception as e:
            QgsMessageLog.logMessage(f"Erro ao tentar corrigir bbox: {str(e)}", "INDE Serviços", level=2)
            
        return bbox

    @classmethod
    def _get_axis_order_crs(cls, crs, wfs_version="2.0.0"):
        """
        Retorna o CRS com a ordem de eixos correta baseada na versão do WFS.
        Para evitar problemas de troca de coordenadas, força longitude/latitude (east/north).
        """
        if not crs:
            return 'EPSG:4326'
            
        # Extrai o código EPSG
        epsg_code = None
        if 'EPSG:' in crs:
            epsg_code = crs.split(':')[1]
        elif 'urn:ogc:def:crs:EPSG::' in crs:
            epsg_code = crs.split('::')[1]
        else:
            epsg_code = crs
            
        # Para CRS geográficos, força longitude/latitude usando formato específico
        if epsg_code in ['4326', '4674', '4618', '4619', '4170']:
            # Usa formato que força longitude/latitude (east/north)
            if wfs_version == "1.0.0":
                # WFS 1.0 usa longitude/latitude por padrão
                return f"EPSG:{epsg_code}"
            else:
                # Para WFS 1.1+ usa formato que força longitude/latitude
                return f"http://www.opengis.net/gml/srs/epsg.xml#{epsg_code}"
        
        return crs

    @classmethod
    def parse_capabilities(cls, root):
        """Parse WFS capabilities document to extract available layers."""
        features = []
        
        # Try multiple paths for FeatureType elements
        feature_type_paths = [
            './/wfs:FeatureType',  # WFS 1.0
            './/FeatureType',      # Without namespace
            './/wfs1:FeatureType'  # WFS 1.x
        ]
        
        feature_types = []
        for path in feature_type_paths:
            feature_types = root.findall(path, cls.NAMESPACES)
            if feature_types:
                QgsMessageLog.logMessage(f"Found feature types using path: {path}", "INDE Serviços", level=3)
                break
                
        QgsMessageLog.logMessage(f"Found {len(feature_types)} feature types", "INDE Serviços", level=3)
                
        for feature_type in feature_types:
            # Try multiple paths for name and title
            name = cls._get_text(feature_type, [
                'wfs:Name',
                'Name',
                'n',  # Handle incorrect tag
                './/n'  # Handle nested incorrect tag
            ])
            
            # If still no name, try to get it from attributes
            if not name:
                name = feature_type.get('name') or feature_type.get('Name')
            
            # If still no name, try to find any text content
            if not name:
                # Look for any child element that might contain the name
                for child in feature_type:
                    if child.text and child.text.strip():
                        name = child.text.strip()
                        QgsMessageLog.logMessage(f"Found name from child element '{child.tag}': {name}", "INDE Serviços", level=3)
                        break
            
            title = cls._get_text(feature_type, [
                'wfs:Title',
                'Title',
                'ows:Title'
            ])
            
            if name:
                # Store the full name with namespace and the local name separately
                namespace = None
                local_name = name
                if ':' in name:
                    namespace, local_name = name.split(':', 1)  # Split only on first colon
                    
                # Extract CRS information
                crs = cls._extract_crs(feature_type)
                
                # Extract bounding box information if available
                bbox = None
                bbox_elem = feature_type.find('.//ows:WGS84BoundingBox', cls.NAMESPACES)
                if bbox_elem is not None:
                    lower = cls._get_text(bbox_elem, ['ows:LowerCorner'])
                    upper = cls._get_text(bbox_elem, ['ows:UpperCorner'])
                    if lower and upper:
                        bbox = {
                            'lower': lower.split(),
                            'upper': upper.split()
                        }
                        # Corrige a ordem das coordenadas se necessário
                        bbox = cls._fix_bbox_coordinates(bbox, crs)
                    
                features.append({
                    'name': local_name,
                    'full_name': name,  # Store the original full name with namespace
                    'namespace': namespace,
                    'title': title or local_name,
                    'crs': crs,
                    'bbox': bbox
                })
                
                QgsMessageLog.logMessage(f"Processed feature: name='{local_name}', full_name='{name}', namespace='{namespace}'", "INDE Serviços", level=3)
            else:
                # Log the raw XML of this feature type for debugging
                QgsMessageLog.logMessage(f"Could not extract name from feature type. Raw XML:", "INDE Serviços", level=2)
                QgsMessageLog.logMessage(ET.tostring(feature_type, encoding='unicode')[:500], "INDE Serviços", level=2)

        return features

    @classmethod
    def load_layer(cls, url, layer_name, display_name=None):
        """Load a WFS layer into QGIS."""
        from qgis.core import QgsVectorLayer, QgsProject, QgsMessageLog
        
        # First, get the layer's CRS from GetCapabilities
        # Extract base URL without parameters
        base_url = url.split('?')[0]
        
        # Construct GetCapabilities URL with WFS 1.0.0
        capabilities_url = f"{base_url}?service=WFS&version=1.0.0&request=GetCapabilities"
        QgsMessageLog.logMessage(f"GetCapabilities URL: {capabilities_url}", "INDE Serviços", level=3)
        
        try:
            response = requests.get(capabilities_url)
            QgsMessageLog.logMessage(f"GetCapabilities Response Status: {response.status_code}", "INDE Serviços", level=3)
            
            # Log the first part of the response for debugging
            response_text = response.text
            QgsMessageLog.logMessage(f"GetCapabilities Response Content (first 1000 chars): {response_text[:1000]}", "INDE Serviços", level=3)
            
            # Check if response is an ExceptionReport
            if "ExceptionReport" in response_text:
                QgsMessageLog.logMessage("GetCapabilities returned an ExceptionReport. Response content:", "INDE Serviços", level=1)
                QgsMessageLog.logMessage(response_text, "INDE Serviços", level=1)
                return None
            
            # Try to parse the XML
            try:
                root = ET.fromstring(response.content)
                QgsMessageLog.logMessage(f"Successfully parsed XML. Root element tag: {root.tag}", "INDE Serviços", level=3)
                
                # Log all namespaces found in the document
                # Extract namespaces from the root element
                namespaces = {}
                for elem in root.iter():
                    for prefix, uri in elem.nsmap.items() if hasattr(elem, 'nsmap') else []:
                        if prefix not in namespaces:
                            namespaces[prefix] = uri
                            QgsMessageLog.logMessage(f"Found namespace: {prefix} = {uri}", "INDE Serviços", level=3)
                
                # Also try to find namespaces in the root element's attributes
                for key, value in root.attrib.items():
                    if key.startswith('xmlns:'):
                        prefix = key[6:]  # Remove 'xmlns:' prefix
                        namespaces[prefix] = value
                        QgsMessageLog.logMessage(f"Found namespace in attributes: {prefix} = {value}", "INDE Serviços", level=3)
            except ET.ParseError as e:
                QgsMessageLog.logMessage(f"Error parsing XML: {str(e)}", "INDE Serviços", level=1)
                QgsMessageLog.logMessage("Raw response content:", "INDE Serviços", level=1)
                QgsMessageLog.logMessage(response_text, "INDE Serviços", level=1)
                return None
                
            # Try to find FeatureType elements with different paths
            feature_type_paths = [
                './/wfs:FeatureType',  # WFS 1.0
                './/FeatureType',      # Without namespace
                './/wfs1:FeatureType'  # WFS 1.x
            ]
            
            feature_types = []
            for path in feature_type_paths:
                try:
                    found = root.findall(path, cls.NAMESPACES)
                    if found:
                        QgsMessageLog.logMessage(f"Found {len(found)} feature types using path: {path}", "INDE Serviços", level=3)
                        feature_types = found
                        break
                except Exception as e:
                    QgsMessageLog.logMessage(f"Error with path {path}: {str(e)}", "INDE Serviços", level=2)
                    continue
            
            if not feature_types:
                QgsMessageLog.logMessage("No feature types found with any path. Available paths in document:", "INDE Serviços", level=1)
                for elem in root.iter():
                    QgsMessageLog.logMessage(f"Found element: {elem.tag}", "INDE Serviços", level=1)
                return None
                
            features = cls.parse_capabilities(root)
            
            # Log available layers for debugging
            QgsMessageLog.logMessage(f"Available layers:", "INDE Serviços", level=3)
            for f in features:
                QgsMessageLog.logMessage(f"  - name: '{f['name']}', full_name: '{f['full_name']}', namespace: '{f['namespace']}'", "INDE Serviços", level=3)
            
            # Try to find the layer with different name formats
            layer_info = None
            
            # Try exact match first
            for f in features:
                if f['name'].lower() == layer_name.lower() or f['full_name'].lower() == layer_name.lower():
                    layer_info = f
                    QgsMessageLog.logMessage(f"Found exact match! Using layer: {f['full_name']}", "INDE Serviços", level=3)
                    break
            
            # If no exact match, try partial matches
            if not layer_info:
                for f in features:
                    if layer_name.lower() in f['name'].lower() or layer_name.lower() in f['full_name'].lower():
                        layer_info = f
                        QgsMessageLog.logMessage(f"Found partial match! Using layer: {f['full_name']}", "INDE Serviços", level=3)
                        break
                    
            if not layer_info:
                QgsMessageLog.logMessage(f"Layer {layer_name} not found in capabilities. Available layers:", "INDE Serviços", level=1)
                for f in features:
                    QgsMessageLog.logMessage(f"  - {f['name']} (full_name: {f['full_name']})", "INDE Serviços", level=1)
                return None
                
            crs = layer_info['crs']
            bbox = layer_info.get('bbox')
            
            # Use the full name (with namespace) from GetCapabilities
            type_name = layer_info['full_name']
            
            QgsMessageLog.logMessage(f"Found layer: {type_name} with CRS: {crs}", "INDE Serviços", level=3)
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error getting capabilities: {str(e)}", "INDE Serviços", level=1)
            return None

        # Extract base URL without parameters
        base_url = url.split('?')[0]
        
        # Use only WFS 1.0.0 with GML formats
        wfs_configs = [
            # GML2 format (longitude/latitude by default in WFS 1.0)
            {
                'version': '1.0.0',
                'formats': ['GML2'],
                'description': 'WFS 1.0.0 + GML2 (longitude/latitude)'
            },
            # GML3 format (latitude/longitude)
            {
                'version': '1.0.0',
                'formats': ['GML3'],
                'description': 'WFS 1.0.0 + GML3 (latitude/longitude)'
            }
        ]
        
        layer = None
        for config in wfs_configs:
            QgsMessageLog.logMessage(f"Trying {config['description']}", "INDE Serviços", level=3)
            
            for output_format in config['formats']:
                # Build URI with minimal parameters
                uri_params = [
                    f"service=WFS",
                    f"version={config['version']}",
                    f"request=GetFeature",
                    f"typeName={type_name}",  # Use the full name with namespace
                    f"outputFormat={output_format}",
                    f"maxFeatures=300000000"
                ]
                
                # Join all parameters
                uri = f"{base_url}?{'&'.join(uri_params)}"
                
                QgsMessageLog.logMessage(f"GetFeature URL construction:", "INDE Serviços", level=3)
                QgsMessageLog.logMessage(f"  Base URL: {base_url}", "INDE Serviços", level=3)
                QgsMessageLog.logMessage(f"  Parameters:", "INDE Serviços", level=3)
                for param in uri_params:
                    QgsMessageLog.logMessage(f"    {param}", "INDE Serviços", level=3)
                QgsMessageLog.logMessage(f"  Final URL: {uri}", "INDE Serviços", level=3)
                
                # Test the GetFeature request before creating the layer
                try:
                    response = requests.get(uri)
                    QgsMessageLog.logMessage(f"GetFeature Response Status: {response.status_code}", "INDE Serviços", level=3)
                    QgsMessageLog.logMessage(f"GetFeature Response Content-Type: {response.headers.get('content-type', 'unknown')}", "INDE Serviços", level=3)
                    
                    # Log first part of response for debugging (GML formats)
                    response_text = response.text
                    QgsMessageLog.logMessage(f"GetFeature Response Content (first 1000 chars): {response_text[:1000]}", "INDE Serviços", level=3)
                    
                    # Check if response is an ExceptionReport
                    if "ExceptionReport" in response_text:
                        QgsMessageLog.logMessage("GetFeature returned an ExceptionReport. Response content:", "INDE Serviços", level=1)
                        QgsMessageLog.logMessage(response_text, "INDE Serviços", level=1)
                        continue
                        
                    # Try to parse as XML to validate (GML formats)
                    try:
                        ET.fromstring(response.content)
                    except ET.ParseError as e:
                        QgsMessageLog.logMessage(f"Error parsing GetFeature response as XML: {str(e)}", "INDE Serviços", level=2)
                        continue
                        
                except Exception as e:
                    QgsMessageLog.logMessage(f"Error testing GetFeature request: {str(e)}", "INDE Serviços", level=2)
                    continue
                
                layer = QgsVectorLayer(uri, display_name or layer_name, "WFS")
                
                if layer.isValid():
                    QgsMessageLog.logMessage(f"Successfully created layer with {config['description']}", "INDE Serviços", level=3)
                    
                    # Set the layer CRS explicitly
                    if crs:
                        layer_crs = QgsCoordinateReferenceSystem(crs)
                        if layer_crs.isValid():
                            layer.setCrs(layer_crs)
                            
                            # If we have bbox info, set the layer extent
                            if bbox:
                                try:
                                    extent = QgsRectangle(
                                        float(bbox['lower'][0]), float(bbox['lower'][1]),
                                        float(bbox['upper'][0]), float(bbox['upper'][1])
                                    )
                                    layer.setExtent(extent)
                                except Exception as e:
                                    QgsMessageLog.logMessage(f"Error setting extent: {str(e)}", "INDE Serviços", level=2)
                    
                    QgsProject.instance().addMapLayer(layer)
                    return layer
                else:
                    QgsMessageLog.logMessage(f"Failed to create valid layer with {config['description']}", "INDE Serviços", level=2)
                    
        return None 