import xml.etree.ElementTree as ET
from qgis.core import QgsMessageLog, Qgis, QgsRasterLayer, QgsProject
from qgis.PyQt.QtWidgets import QMessageBox

class WCSService:
    """Classe para manipular serviços WCS."""
    
    NAMESPACES = {
        'wcs': 'http://www.opengis.net/wcs/1.1',
        'wcs11': 'http://www.opengis.net/wcs/1.1.1',
        'ows': 'http://www.opengis.net/ows/1.1',
        'xlink': 'http://www.w3.org/1999/xlink',
        'gml': 'http://www.opengis.net/gml',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }
    
    @staticmethod
    def parse_capabilities(root):
        """Analisa o documento WCS GetCapabilities."""
        try:
            QgsMessageLog.logMessage("Iniciando parse do WCS Capabilities", "IndeServicosBR", Qgis.Info)
            
            # Log do elemento raiz e seus namespaces
            QgsMessageLog.logMessage(f"Root element tag: {root.tag}", "IndeServicosBR", Qgis.Info)
            
            # Extrair namespaces do elemento raiz
            namespaces = {}
            for key, value in root.attrib.items():
                if key.startswith('xmlns:'):
                    prefix = key[6:]  # Remove 'xmlns:' prefix
                    namespaces[prefix] = value
                    QgsMessageLog.logMessage(f"Found namespace: {prefix} = {value}", "IndeServicosBR", Qgis.Info)
            
            # Tenta diferentes caminhos para encontrar as coverages
            coverage_paths = [
                './/wcs:CoverageSummary',  # WCS 1.1
                './/wcs11:CoverageSummary',  # WCS 1.1.1
                './/CoverageSummary',  # Sem namespace
                './/wcs:Coverage',  # WCS 1.1
                './/wcs11:Coverage',  # WCS 1.1.1
                './/Coverage',  # Sem namespace
                './/*[local-name()="CoverageSummary"]',  # Usando local-name()
                './/*[local-name()="Coverage"]'  # Usando local-name()
            ]
            
            coverage_elements = []
            for path in coverage_paths:
                try:
                    found = root.findall(path, WCSService.NAMESPACES)
                    if found:
                        QgsMessageLog.logMessage(f"Found {len(found)} coverages using path: {path}", "IndeServicosBR", Qgis.Info)
                        coverage_elements = found
                        break
                except Exception as e:
                    QgsMessageLog.logMessage(f"Error with path {path}: {str(e)}", "IndeServicosBR", Qgis.Warning)
                    continue
            
            if not coverage_elements:
                QgsMessageLog.logMessage("No coverages found with any path. Available paths in document:", "IndeServicosBR", Qgis.Warning)
                for elem in root.iter():
                    QgsMessageLog.logMessage(f"Found element: {elem.tag}", "IndeServicosBR", Qgis.Info)
                return []
            
            coverages = []
            for coverage_elem in coverage_elements:
                # Tenta diferentes caminhos para o identificador
                name_elem = None
                for path in [
                    './wcs:Identifier',
                    './wcs11:Identifier',
                    './ows:Identifier',
                    './Identifier',
                    './Name'
                ]:
                    name_elem = coverage_elem.find(path, WCSService.NAMESPACES)
                    if name_elem is not None and name_elem.text:
                        break
                
                # Tenta diferentes caminhos para o título
                title_elem = None
                for path in [
                    './ows:Title',
                    './wcs:Title',
                    './wcs11:Title',
                    './Title'
                ]:
                    title_elem = coverage_elem.find(path, WCSService.NAMESPACES)
                    if title_elem is not None and title_elem.text:
                        break
                
                if name_elem is not None and name_elem.text:
                    coverage_name = name_elem.text
                    coverage_title = title_elem.text if title_elem is not None else coverage_name
                    
                    coverages.append({
                        'name': coverage_name,
                        'title': coverage_title
                    })
                    QgsMessageLog.logMessage(f"Coverage encontrada: {coverage_name} ({coverage_title})", "IndeServicosBR", Qgis.Info)
            
            QgsMessageLog.logMessage(f"Total de coverages processadas: {len(coverages)}", "IndeServicosBR", Qgis.Info)
            return coverages
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Erro ao processar WCS Capabilities: {str(e)}", "IndeServicosBR", Qgis.Critical)
            return []
            
    @staticmethod
    def load_layer(url, coverage_name, display_name):
        """Carrega uma camada WCS no projeto."""
        try:
            # Construir a URI com os parâmetros necessários
            uri_params = [
                f"type=wcs",
                f"url={url}",
                f"identifier={coverage_name}",
                f"version=1.1.1"  # Usar versão mais recente do WCS
            ]
            
            uri = "&".join(uri_params)
            QgsMessageLog.logMessage(f"WCS URI: {uri}", "IndeServicosBR", Qgis.Info)
            
            layer = QgsRasterLayer(uri, display_name, "wcs")
            
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                return True
            else:
                QMessageBox.warning(None, "Erro", "Camada WCS inválida")
                return False
                
        except Exception as e:
            QMessageBox.warning(None, "Erro", f"Erro ao carregar camada WCS: {str(e)}")
            return False 